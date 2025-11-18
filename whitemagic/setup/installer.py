"""Embeddings installation with progress tracking."""

import subprocess
import sys
from typing import Optional

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn


def check_embeddings_installed() -> bool:
    """Check if embeddings package is already installed."""
    try:
        import sentence_transformers

        return True
    except ImportError:
        return False


def install_embeddings_package(console: Console) -> bool:
    """Install whitemagic[embeddings] with progress display.

    Returns:
        True if successful, False otherwise
    """
    console.print("\n[bold]Installing Local AI Package...[/bold]")
    console.print("[dim]This may take a few minutes (~2.5GB download)[/dim]\n")

    try:
        # Run pip install in subprocess
        process = subprocess.Popen(
            [sys.executable, "-m", "pip", "install", "--quiet", "whitemagic[embeddings]"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Installing dependencies...", total=None)

            # Wait for completion
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                progress.update(task, description="[green]✓ Installation complete!")
                return True
            else:
                console.print("\n[red]✗ Installation failed:[/red]")
                console.print(f"[dim]{stderr}[/dim]")
                return False

    except Exception as e:
        console.print(f"\n[red]✗ Installation error: {e}[/red]")
        return False


def download_model(model_name: str, console: Console) -> bool:
    """Download and cache embedding model.

    Args:
        model_name: Model to download (e.g., 'all-MiniLM-L6-v2')
        console: Rich console for output

    Returns:
        True if successful, False otherwise
    """
    console.print(f"\n[bold]Downloading Model: {model_name}...[/bold]")
    console.print("[dim]This will be cached for future use[/dim]\n")

    try:
        from sentence_transformers import SentenceTransformer

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"Downloading {model_name}...", total=None)

            # This will download and cache the model
            model = SentenceTransformer(model_name)

            progress.update(task, description=f"[green]✓ Model ready: {model_name}!")

        console.print("\n[green]✓ Model cached successfully![/green]")
        return True

    except Exception as e:
        console.print(f"\n[red]✗ Model download failed: {e}[/red]")
        return False


def prompt_openai_key(console: Console) -> Optional[str]:
    """Prompt user for OpenAI API key.

    Returns:
        API key if entered, None if skipped
    """
    import getpass

    console.print("\n[bold]OpenAI API Key Required[/bold]")
    console.print("Get your key at: [link]https://platform.openai.com/api-keys[/link]\n")

    try:
        api_key = getpass.getpass("Enter API key (or press Enter to skip): ")
        if api_key:
            console.print("[green]✓ API key received[/green]")
            return api_key
        else:
            console.print("[yellow]○ Skipped - you can set it later with:[/yellow]")
            console.print("[cyan]  export OPENAI_API_KEY=sk-...[/cyan]\n")
            return None
    except KeyboardInterrupt:
        console.print("\n[yellow]Skipped[/yellow]")
        return None
