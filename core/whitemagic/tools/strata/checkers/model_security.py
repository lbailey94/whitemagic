"""Model file format security checkers — targets huntr.com MFV bounties.

Detects vulnerabilities in ML model loading, deserialization, and file format
handling across Python ML libraries (PyTorch, TensorFlow, Keras, ONNX, Pickle,
SafeTensors, Hugging Face, joblib, numpy).
"""
import re
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity

# ── Unsafe Deserialization Patterns ──────────────────────────────────

_PICKLE_CALLS = re.compile(
    r"\b(pickle\.load|pickle\.loads|cPickle\.load|cPickle\.loads|"
    r"_pickle\.load|_pickle\.loads|dill\.load|dill\.loads|"
    r"shelve\.open|marshal\.load|marshal\.loads)\s*\(",
)

_JOBLIB_CALLS = re.compile(
    r"\b(joblib\.load|sklearn\.externals\.joblib\.load)\s*\(",
)

_JOBLIB_IMPORT = re.compile(
    r"\bfrom\s+joblib\s+import\s+load\b",
)

_TORCH_LOAD_CALLS = re.compile(
    r"\b(torch\.load|torch\.jit\.load|torch\.nn\.modules\.module\.load_state_dict)\s*\(",
)

_TF_LOAD_CALLS = re.compile(
    r"\b(tf\.keras\.models\.load_model|keras\.models\.load_model|"
    r"tf\.saved_model\.load|tf\.train\.load_checkpoint|"
    r"hub\.load|tensorflow_hub\.load)\s*\(",
)

_HF_LOAD_CALLS = re.compile(
    r"\b(from_pretrained|AutoModel\.from_pretrained|AutoTokenizer\.from_pretrained|"
    r"pipeline\s*\(|safetensors\.load_file|safetensors\.safe_open)\s*\(",
)

_ONNX_CALLS = re.compile(
    r"\b(onnx\.load|onnx\.load_model|onnx\.hub\.load_model|onnxruntime\.InferenceSession)\s*\(",
)

_NUMPY_LOAD = re.compile(
    r"\b(np\.load|numpy\.load)\s*\(",
)

# Weights only (safe) vs full object loading (unsafe)
_WEIGHTS_ONLY_SAFE = re.compile(r"weights_only\s*=\s*True")
_PICKLE_SAFE_ALTS = re.compile(
    r"safetensors|torch\.load.*weights_only\s*=\s*True|"
    r"from_pretrained.*use_safetensors\s*=\s*True",
    re.IGNORECASE,
)

# ── Path Traversal in Model Loading ──────────────────────────────────

_USER_INPUT_IN_PATH = re.compile(
    r"\b(request\.|input\s*\(|argv|getenv|os\.environ|sys\.argv|"
    r"args\.|kwargs\.|config\[|config\.get|os\.path\.join\s*\(\s*(?:request\.|args\.|input))",
)

_PATH_SAFE = re.compile(
    r"safe_join|secure_filename|sanitize|validate|whitelist|allowed|resolve|"
    r"Path\s*\(\s*\)\.resolve|abspath|realpath|normpath",
    re.IGNORECASE,
)

# ── Arbitrary Code Execution in Model Formats ────────────────────────

_EXEC_PATTERNS = re.compile(
    r"\b(exec\s*\(|eval\s*\(|compile\s*\(|__import__\s*\(|"
    r"os\.system\s*\(|subprocess\.(call|run|Popen|check_output)\s*\(|"
    r"os\.popen\s*\(|__builtins__|__subclasses__|"
    r"globals\s*\(\s*\)|locals\s*\(\s*\)|"
    r"getattr\s*\(\s*(?:obj|self|module|cls)\s*,\s*['\"]__(?:class|subclasses|builtins|globals)__['\"]\s*\))",
)

# Keras Lambda layers — known RCE vector
_KERAS_LAMBDA = re.compile(
    r"\b(Lambda\s*\(|tf\.keras\.layers\.Lambda\s*\(|keras\.layers\.Lambda\s*\()",
)

# Custom objects in Keras model loading — can execute arbitrary code
_KERAS_CUSTOM = re.compile(
    r"custom_objects\s*=\s*\{",
)

# __reduce__ / __reduce_ex__ — pickle exploit vector
_REDUCE_PATTERN = re.compile(
    r"__reduce__\s*\(|__reduce_ex__\s*\(",
)

# Unsafe YAML loading (PyYAML) — used in some model configs
_UNSAFE_YAML = re.compile(
    r"\byaml\.load\s*\((?!.*Loader\s*=)",
)

# TensorFlow saved model — unsafe if loading from untrusted source
_TF_SAVED_MODEL_UNSAFE = re.compile(
    r"\btf\.saved_model\.load\s*\(",
)

# Hugging Face — trust_remote_code=True is dangerous
_HF_TRUST_REMOTE = re.compile(
    r"trust_remote_code\s*=\s*True",
)

# ── Pickle File Detection ────────────────────────────────────────────

_PICKLE_MAGIC = b"\x80\x02\x00"  # Protocol 2 header (common in ML)
_PICKLE_EXT = {".pkl", ".pickle", ".pt", ".pth", ".bin", ".ckpt", ".safetensors"}


@register
def check_unsafe_pickle_deserialization(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect unsafe pickle/marshal/dill deserialization — RCE via crafted files."""
    for py_file in file_index.files_by_extension(".py"):
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(py_file.relative_to(project_path))
        lines = content.splitlines()
        joblib_imported = False
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _JOBLIB_IMPORT.search(line):
                joblib_imported = True
            if _PICKLE_CALLS.search(line):
                if _PICKLE_SAFE_ALTS.search(line):
                    continue
                findings.append(
                    Finding(
                        severity=FindingSeverity.ERROR,
                        category="unsafe_deserialization",
                        file=rel,
                        line=i,
                        message="Unsafe pickle/marshal/dill deserialization — arbitrary code execution via crafted files.",
                        suggestion="Use safetensors or weights_only=True. Never unpickle untrusted data.",
                    )
                )
            elif _JOBLIB_CALLS.search(line):
                findings.append(
                    Finding(
                        severity=FindingSeverity.ERROR,
                        category="unsafe_deserialization",
                        file=rel,
                        line=i,
                        message="joblib.load uses pickle internally — RCE risk with untrusted files.",
                        suggestion="Validate file source before loading. Consider using safetensors or numpy formats.",
                    )
                )
            elif joblib_imported and re.search(r"\bload\s*\(", line) and not _PICKLE_SAFE_ALTS.search(line):
                findings.append(
                    Finding(
                        severity=FindingSeverity.ERROR,
                        category="unsafe_deserialization",
                        file=rel,
                        line=i,
                        message="joblib.load (via from-import) uses pickle internally — RCE risk with untrusted files.",
                        suggestion="Validate file source before loading. Consider using safetensors or numpy formats.",
                    )
                )


@register
def check_unsafe_torch_load(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect torch.load without weights_only=True — pickle-based RCE."""
    for py_file in file_index.files_by_extension(".py"):
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(py_file.relative_to(project_path))
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _TORCH_LOAD_CALLS.search(line):
                if _WEIGHTS_ONLY_SAFE.search(line):
                    continue
                # Check surrounding context for weights_only on next line
                if i < len(lines) and _WEIGHTS_ONLY_SAFE.search(lines[i]):
                    continue
                findings.append(
                    Finding(
                        severity=FindingSeverity.ERROR,
                        category="unsafe_torch_load",
                        file=rel,
                        line=i,
                        message="torch.load without weights_only=True — uses pickle, RCE risk with crafted checkpoints.",
                        suggestion="Use torch.load(path, weights_only=True) or migrate to safetensors format.",
                    )
                )


@register
def check_unsafe_keras_load(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect unsafe Keras model loading — Lambda layers and custom_objects can execute arbitrary code."""
    for py_file in file_index.files_by_extension(".py"):
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(py_file.relative_to(project_path))
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _TF_LOAD_CALLS.search(line):
                findings.append(
                    Finding(
                        severity=FindingSeverity.WARNING,
                        category="unsafe_keras_load",
                        file=rel,
                        line=i,
                        message="Keras model loading — Lambda layers and custom_objects can execute arbitrary code.",
                        suggestion="Only load models from trusted sources. Audit custom_objects for code execution.",
                    )
                )
            if _KERAS_LAMBDA.search(line):
                findings.append(
                    Finding(
                        severity=FindingSeverity.WARNING,
                        category="keras_lambda_rce",
                        file=rel,
                        line=i,
                        message="Keras Lambda layer — can execute arbitrary Python code during model loading/inference.",
                        suggestion="Avoid Lambda layers in models from untrusted sources. Use custom layer subclasses instead.",
                    )
                )
            if _KERAS_CUSTOM.search(line):
                findings.append(
                    Finding(
                        severity=FindingSeverity.INFO,
                        category="keras_custom_objects",
                        file=rel,
                        line=i,
                        message="custom_objects in Keras load — verify no code execution in custom classes.",
                        suggestion="Audit each custom_objects entry for __init__, call, and deserialize methods.",
                    )
                )


@register
def check_hf_trust_remote_code(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect trust_remote_code=True in Hugging Face loading — executes arbitrary code from model repo."""
    for py_file in file_index.files_by_extension(".py"):
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(py_file.relative_to(project_path))
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _HF_LOAD_CALLS.search(line) and _HF_TRUST_REMOTE.search(line):
                findings.append(
                    Finding(
                        severity=FindingSeverity.ERROR,
                        category="hf_trust_remote_code",
                        file=rel,
                        line=i,
                        message="trust_remote_code=True in Hugging Face load — executes arbitrary Python from model repository.",
                        suggestion="Set trust_remote_code=False. Only use models with verified, safe code.",
                    )
                )
            elif _HF_LOAD_CALLS.search(line) and not _WEIGHTS_ONLY_SAFE.search(line):
                # Check if it's a model load (not just tokenizer) that could be unsafe
                if re.search(r"AutoModel|from_pretrained.*model", line, re.IGNORECASE):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.INFO,
                            category="hf_model_load",
                            file=rel,
                            line=i,
                            message="Hugging Face model load — verify use_safetensors=True to avoid pickle-based formats.",
                            suggestion="Prefer safetensors format: from_pretrained(model, use_safetensors=True).",
                        )
                    )


@register
def check_model_path_traversal(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect path traversal in model file loading — user input in model paths."""
    for py_file in file_index.files_by_extension(".py"):
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(py_file.relative_to(project_path))
        lines = content.splitlines()
        # Track variables assigned from user input
        user_vars: set[str] = set()
        safe_vars: set[str] = set()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Track assignments from user input: var = request.args.get(...)
            assign_match = re.match(
                r"(\w+)\s*=\s*.*(?:request\.|input\s*\(|argv|getenv|os\.environ|args\.|kwargs\.)",
                line,
            )
            if assign_match:
                var_name = assign_match.group(1)
                if _PATH_SAFE.search(line):
                    safe_vars.add(var_name)
                else:
                    user_vars.add(var_name)
            # Check if line has model loading
            model_load = (
                _TORCH_LOAD_CALLS.search(line)
                or _TF_LOAD_CALLS.search(line)
                or _HF_LOAD_CALLS.search(line)
                or _ONNX_CALLS.search(line)
                or _PICKLE_CALLS.search(line)
                or _JOBLIB_CALLS.search(line)
                or _NUMPY_LOAD.search(line)
            )
            if not model_load:
                continue
            # Check for direct user input or tracked user vars in the line
            has_user_input = _USER_INPUT_IN_PATH.search(line)
            if not has_user_input:
                for var in user_vars:
                    if var not in safe_vars and re.search(rf"\b{re.escape(var)}\b", line):
                        has_user_input = True
                        break
            if has_user_input and not _PATH_SAFE.search(line):
                findings.append(
                    Finding(
                        severity=FindingSeverity.WARNING,
                        category="model_path_traversal",
                        file=rel,
                        line=i,
                        message="User input in model file path — path traversal risk.",
                        suggestion="Validate and sanitize model paths. Restrict to a trusted model directory.",
                    )
                )


@register
def check_pickle_reduce_exploit(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect __reduce__ methods that could be used for pickle exploit payloads."""
    for py_file in file_index.files_by_extension(".py"):
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(py_file.relative_to(project_path))
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _REDUCE_PATTERN.search(line):
                # Check if it looks like an exploit payload (not just a legitimate serializer)
                context = "\n".join(lines[max(0, i - 3):i + 4])
                if _EXEC_PATTERNS.search(context):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.ERROR,
                            category="pickle_reduce_exploit",
                            file=rel,
                            line=i,
                            message="__reduce__ with code execution — potential pickle exploit payload.",
                            suggestion="Remove __reduce__ if not needed for serialization. Never use exec/eval in __reduce__.",
                        )
                    )


@register
def check_unsafe_yaml_in_model_config(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect unsafe yaml.load without Loader — RCE via crafted YAML model configs."""
    for py_file in file_index.files_by_extension(".py"):
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(py_file.relative_to(project_path))
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _UNSAFE_YAML.search(line):
                findings.append(
                    Finding(
                        severity=FindingSeverity.ERROR,
                        category="unsafe_yaml_load",
                        file=rel,
                        line=i,
                        message="yaml.load without safe Loader — arbitrary code execution via crafted YAML.",
                        suggestion="Use yaml.load(data, Loader=yaml.SafeLoader) or yaml.safe_load(data).",
                    )
                )


@register
def check_onnx_unsafe_load(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect ONNX model loading from untrusted sources — potential for malicious model graphs."""
    for py_file in file_index.files_by_extension(".py"):
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(py_file.relative_to(project_path))
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _ONNX_CALLS.search(line):
                if _USER_INPUT_IN_PATH.search(line) and not _PATH_SAFE.search(line):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.WARNING,
                            category="onnx_unsafe_load",
                            file=rel,
                            line=i,
                            message="ONNX model loaded from user-controlled path — malicious model graph risk.",
                            suggestion="Only load ONNX models from trusted registries. Validate model graph before inference.",
                        )
                    )


@register
def check_numpy_unsafe_load(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect numpy.load without allow_pickle=False — pickle-based RCE."""
    for py_file in file_index.files_by_extension(".py"):
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(py_file.relative_to(project_path))
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _NUMPY_LOAD.search(line):
                if "allow_pickle" in line and "allow_pickle" in line:
                    # Check if allow_pickle=True (unsafe)
                    if re.search(r"allow_pickle\s*=\s*True", line):
                        findings.append(
                            Finding(
                                severity=FindingSeverity.ERROR,
                                category="numpy_unsafe_load",
                                file=rel,
                                line=i,
                                message="numpy.load with allow_pickle=True — pickle-based RCE via crafted .npy files.",
                                suggestion="Use allow_pickle=False (default). Use np.save/np.load with explicit dtype.",
                            )
                        )
                else:
                    # Default is allow_pickle=False since numpy 1.16.3, but .npy with object arrays still use pickle
                    if re.search(r"\.npy|\.npz", line):
                        findings.append(
                            Finding(
                                severity=FindingSeverity.INFO,
                                category="numpy_object_array",
                                file=rel,
                                line=i,
                                message="numpy.load of .npy/.npz file — object arrays use pickle internally.",
                                suggestion="Ensure loaded files are from trusted sources. Avoid object dtype arrays.",
                            )
                        )


@register
def check_pickle_files_in_repo(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect pickle/model files committed to repository — potential trojan models."""
    for ext in _PICKLE_EXT:
        for model_file in file_index.files_by_extension(ext):
            try:
                rel = str(model_file.relative_to(project_path))
            except ValueError:
                rel = str(model_file)
            # Skip if in a test/fixtures directory
            if re.search(r"test|fixture|example|sample|demo", rel, re.IGNORECASE):
                continue
            findings.append(
                Finding(
                    severity=FindingSeverity.INFO,
                    category="pickle_file_in_repo",
                    file=rel,
                    line=None,
                    message=f"Model file ({ext}) in repository — verify it's not a trojan model with embedded pickle payload.",
                    suggestion="Prefer safetensors format. Scan model files with model_signing before use.",
                )
            )
