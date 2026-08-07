#!/usr/bin/env python3
"""
LoRA Fine-Tuning Script for WhiteMagic v4

Uses self-verified calibration data exported from the inference router
to fine-tune a small model (e.g., SmolLM2-360M) with LoRA adapters.

The training data is collected during self-verification: when the model
verifies its own answer as correct, the (prompt, response) pair becomes
a positive training example. This creates a self-improving loop where
the model learns from its own verified successes.

Usage:
    # Export training data from WhiteMagic
    wm export-training-data --output training_data.jsonl --format jsonl

    # Run LoRA fine-tuning
    python scripts/lora_finetune.py \
        --model /home/lucas/models/smollm2-360m/ \
        --data training_data.jsonl \
        --output lora_adapter.bin \
        --epochs 3 \
        --lr 2e-4

    # Hot-swap: restart llama-server with the LoRA adapter
    llama-server --model /home/lucas/models/smollm2-360m/ggml-model-q4_k_m.gguf \
        --lora lora_adapter.bin \
        --port 8081

Prerequisites:
    pip install torch transformers peft datasets accelerate
"""

import argparse
import json
import os
import sys
from pathlib import Path


def load_training_data(filepath: str) -> list[dict]:
    """Load JSONL training data exported from WhiteMagic."""
    samples = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            sample = json.loads(line)
            samples.append(sample)
    print(f"Loaded {len(samples)} training samples from {filepath}")
    return samples


def prepare_dataset(samples: list[dict], tokenizer, max_length: int = 512):
    """Convert raw samples into a tokenized dataset for fine-tuning."""
    from torch.utils.data import Dataset

    class TrainingDataset(Dataset):
        def __init__(self, samples, tokenizer, max_length):
            self.samples = samples
            self.tokenizer = tokenizer
            self.max_length = max_length

        def __len__(self):
            return len(self.samples)

        def __getitem__(self, idx):
            sample = self.samples[idx]

            # Handle both JSONL formats
            if "messages" in sample:
                # OpenAI chat format
                prompt = sample["messages"][0]["content"]
                response = sample["messages"][1]["content"]
            elif "prompt" in sample and "completion" in sample:
                # llama.cpp format
                prompt = sample["prompt"]
                response = sample["completion"]
            else:
                prompt = sample.get("prompt", "")
                response = sample.get("response", "")

            # Format as instruction + response
            text = f"### User:\n{prompt}\n\n### Assistant:\n{response}"

            encoding = self.tokenizer(
                text,
                truncation=True,
                max_length=self.max_length,
                padding="max_length",
                return_tensors="pt",
            )

            # Use the full text as labels (causal LM)
            labels = encoding["input_ids"].clone()

            return {
                "input_ids": encoding["input_ids"].squeeze(),
                "attention_mask": encoding["attention_mask"].squeeze(),
                "labels": labels.squeeze(),
            }

    return TrainingDataset(samples, tokenizer, max_length)


def train_lora(
    model_path: str,
    data_path: str,
    output_path: str,
    epochs: int,
    lr: float,
    batch_size: int,
    max_length: int,
    lora_r: int,
    lora_alpha: int,
):
    """Run LoRA fine-tuning on the model."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
    from peft import LoraConfig, get_peft_model, TaskType
    from torch.utils.data import DataLoader

    print(f"Loading model from {model_path}...")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float16,
        device_map="auto",
    )

    # Configure LoRA
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Load and prepare data
    samples = load_training_data(data_path)
    if len(samples) < 10:
        print(f"Warning: only {len(samples)} samples. Need at least 10 for meaningful training.")
        if len(samples) == 0:
            print("No training data. Export data first with: wm export-training-data --output ...")
            sys.exit(1)

    dataset = prepare_dataset(samples, tokenizer, max_length)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    # Training loop
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    model.train()

    step = 0
    for epoch in range(epochs):
        epoch_loss = 0.0
        for batch in dataloader:
            input_ids = batch["input_ids"].to(model.device)
            attention_mask = batch["attention_mask"].to(model.device)
            labels = batch["labels"].to(model.device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )
            loss = outputs.loss

            loss.backward()
            optimizer.step()
            optimizer.zero_grad()

            epoch_loss += loss.item()
            step += 1

            if step % 10 == 0:
                print(f"  Epoch {epoch+1}/{epochs}, Step {step}, Loss: {loss.item():.4f}")

        avg_loss = epoch_loss / len(dataloader)
        print(f"Epoch {epoch+1}/{epochs} complete — avg loss: {avg_loss:.4f}")

    # Save LoRA adapter
    print(f"Saving LoRA adapter to {output_path}...")
    model.save_pretrained(output_path)
    print("Done!")

    # Print hot-swap instructions
    print()
    print("=== Hot-Swap Instructions ===")
    print(f"1. Stop the current llama-server:")
    print(f"   pkill -f 'llama-server.*8081'")
    print(f"2. Restart with LoRA adapter:")
    print(f"   llama-server \\")
    print(f"     --model {model_path}/ggml-model-q4_k_m.gguf \\")
    print(f"     --lora {output_path}/adapter_model.bin \\")
    print(f"     --port 8081")
    print(f"3. Verify: wm stats")


def convert_to_gguf(adapter_path: str, model_path: str):
    """Convert HuggingFace LoRA adapter to GGUF format for llama.cpp."""
    print(f"Converting LoRA adapter to GGUF format...")
    print(f"  Adapter: {adapter_path}")
    print(f"  Base model: {model_path}")
    print()
    print("Use llama.cpp's export-lora tool:")
    print(f"  python convert_lora_to_gguf.py {adapter_path}")
    print()
    print("Or if using the built-in converter:")
    print(f"  ./build/bin/export-lora --model {model_path} --lora {adapter_path}")


def main():
    parser = argparse.ArgumentParser(
        description="LoRA fine-tuning for WhiteMagic v4 self-verified training data"
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Path to base model (HuggingFace format)",
    )
    parser.add_argument(
        "--data",
        type=str,
        required=True,
        help="Path to training data JSONL file (from wm export-training-data)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="lora_adapter",
        help="Output directory for LoRA adapter (default: lora_adapter)",
    )
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size")
    parser.add_argument("--max-length", type=int, default=512, help="Max sequence length")
    parser.add_argument("--lora-r", type=int, default=8, help="LoRA rank")
    parser.add_argument("--lora-alpha", type=int, default=16, help="LoRA alpha")
    parser.add_argument(
        "--convert-gguf",
        action="store_true",
        help="Print GGUF conversion instructions after training",
    )

    args = parser.parse_args()

    train_lora(
        model_path=args.model,
        data_path=args.data,
        output_path=args.output,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
        max_length=args.max_length,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
    )

    if args.convert_gguf:
        convert_to_gguf(args.output, args.model)


if __name__ == "__main__":
    main()
