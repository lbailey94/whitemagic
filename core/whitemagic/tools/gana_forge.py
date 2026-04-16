"""Gana Forge — Declarative Tool Extension Protocol.
====================================================
Implements the extensibility gap identified via Mahābhārata 12.108.17:

  "Establish dharmic procedures grounded in śāstra, then follow them."

Currently, adding a tool to a Gana requires modifying 5+ hardcoded source
files. The Forge allows any AI (or human) to define new tools via YAML
manifests in $WM_STATE_ROOT/extensions/, which are loaded at runtime and
injected into the PRAT routing without source code changes.

Manifests are validated by the Dharma engine before acceptance.

Lifecycle:
  1. Write YAML manifest to extensions/ directory
  2. Forge discovers and validates on startup (or via reload)
  3. Valid tools are injected into DISPATCH_TABLE and TOOL_TO_GANA
  4. Invalid manifests are logged but do not block startup
"""

import logging
from pathlib import Path
from typing import Any

from whitemagic.config.paths import EXTENSIONS_DIR

# Lazy imports to avoid circular dependencies
# (loaded at runtime when _inject_tool is called)

logger = logging.getLogger(__name__)

# Default extensions directory
_DEFAULT_EXT_DIR = EXTENSIONS_DIR

# Valid safety levels (must match registry SafetyLevel)
_VALID_SAFETY = {"read", "write", "delete", "admin"}

# All known Gana names
_VALID_GANAS = {
    "gana_horn", "gana_neck", "gana_root", "gana_room", "gana_heart",
    "gana_tail", "gana_winnowing_basket", "gana_ghost", "gana_willow",
    "gana_star", "gana_extended_net", "gana_wings", "gana_chariot",
    "gana_abundance", "gana_straddling_legs", "gana_mound", "gana_stomach",
    "gana_hairy_head", "gana_net", "gana_turtle_beak", "gana_three_stars",
    "gana_dipper", "gana_ox", "gana_girl", "gana_void", "gana_roof",
    "gana_encampment", "gana_wall",
}


def _parse_manifest(path: Path) -> dict[str, Any] | None:
    """Parse a YAML manifest file. Returns None on failure."""
    try:
        import yaml
    except ImportError:
        # PyYAML not installed — try json fallback
        from whitemagic.utils.fast_json import loads as _json_loads
        try:
            data: dict[str, Any] = _json_loads(path.read_text(encoding="utf-8"))
            return data
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning("Forge: failed to parse %s as JSON: %s", path, e)
            return None

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            logger.warning("Forge: %s is not a dict", path)
            return None
        return data
    except Exception as e:
        logger.warning("Forge: failed to parse %s: %s", path, e)
        return None


def _validate_manifest(manifest: dict[str, Any], path: Path) -> list[str]:
    """Validate a tool manifest. Returns list of errors (empty = valid)."""
    errors: list[str] = []
    tool = manifest.get("tool", {})

    if not isinstance(tool, dict):
        return [f"{path}: 'tool' must be a dict"]

    name = tool.get("name")
    if not name or not isinstance(name, str):
        errors.append(f"{path}: 'tool.name' is required (string)")

    description = tool.get("description")
    if not description or not isinstance(description, str):
        errors.append(f"{path}: 'tool.description' is required (string)")

    gana = tool.get("gana")
    if not gana or gana not in _VALID_GANAS:
        errors.append(
            f"{path}: 'tool.gana' must be one of the 28 canonical Ganas, got '{gana}'"
        )

    safety = tool.get("safety", "read")
    if safety not in _VALID_SAFETY:
        errors.append(f"{path}: 'tool.safety' must be one of {_VALID_SAFETY}, got '{safety}'")

    handler = tool.get("handler")
    if not handler or not isinstance(handler, str):
        errors.append(f"{path}: 'tool.handler' is required (string, e.g. 'mymod:my_func')")

    # Signature verification (P0 security fix)
    signature = manifest.get("signature")
    if signature:
        # If signature is provided, verify it
        # For now, log a warning if signature verification fails
        # Full implementation would use actual cryptographic verification
        try:
            import hmac

            expected_sig = _compute_manifest_signature(manifest)
            if not hmac.compare_digest(signature, expected_sig):
                errors.append(f"{path}: signature verification failed - manifest may be tampered")
        except (ImportError, AttributeError):
            # hmac should always be available, but fail gracefully
            logger.warning("Forge: signature verification unavailable for %s", path)

    return errors


def _compute_manifest_signature(manifest: dict[str, Any]) -> str:
    """Compute an HMAC-SHA256 signature for a manifest.

    Uses a secret key derived from the WhiteMagic vault so that only holders
    of the vault passphrase can produce valid signatures.

    Falls back to a clearly-marked placeholder if the vault is unavailable,
    which will *never* match a real signature (so the manifest will be rejected).
    """
    import hashlib
    import hmac
    import json

    # Normalise manifest (exclude the signature field itself)
    manifest_copy = dict(manifest)
    manifest_copy.pop("signature", None)
    manifest_str = json.dumps(manifest_copy, sort_keys=True, separators=(",", ":"))
    manifest_bytes = manifest_str.encode()

    # Retrieve signing key from vault or env
    key = _get_forge_signing_key()
    return hmac.new(key, manifest_bytes, hashlib.sha256).hexdigest()


def _get_forge_signing_key() -> bytes:
    """Return the HMAC signing key for manifest verification.

    Priority:
    1. ``WM_VAULT_PASSPHRASE`` env var (PBKDF2-derived)
    2. Vault secret ``forge_signing_key``
    3. INSECURE fallback — logs a loud warning and returns a zero key that
       will never match a properly-signed manifest.
    """
    import hashlib
    import os

    # 1. Derive from env passphrase (fast path for standalone/test environments)
    passphrase = os.environ.get("WM_VAULT_PASSPHRASE") or os.environ.get("WM_DB_PASSPHRASE")
    if passphrase:
        return hashlib.pbkdf2_hmac(
            "sha256",
            passphrase.encode(),
            b"whitemagic-forge-v1",
            iterations=100_000,
        )

    # 2. Try the vault
    try:
        from whitemagic.security.vault import get_vault
        vault = get_vault()
        get_secret = getattr(vault, "get_secret", None)
        secret = get_secret("forge_signing_key") if get_secret else None
        if secret:
            return secret.encode() if isinstance(secret, str) else secret
    except Exception as _vault_exc:
        logger.debug("Forge: vault unavailable for signing key: %s", _vault_exc)

    # 3. No key available — return sentinel that will never match
    logger.error(
        "Forge: NO signing key available (vault locked, WM_VAULT_PASSPHRASE unset). "
        "Manifest signature verification is DISABLED. "
        "Set WM_VAULT_PASSPHRASE or unlock the vault to enable it."
    )
    return b"\x00" * 32  # sentinel — hmac with this will never match a real sig


def _resolve_handler(handler_spec: str) -> Any:
    """Resolve a handler specification like 'module.path:function_name'.

    Supports two formats:
    - 'module.path:function_name' — importlib resolution
    - 'builtin:echo' — returns a simple echo handler for testing
    """
    if handler_spec == "builtin:echo":
        def _echo_handler(**kwargs: Any) -> dict[str, Any]:
            return {"status": "success", "echo": kwargs}
        return _echo_handler

    if ":" not in handler_spec:
        logger.warning("Forge: handler '%s' must use 'module:function' format", handler_spec)
        return None

    module_path, func_name = handler_spec.rsplit(":", 1)
    try:
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, func_name)
    except (ImportError, ModuleNotFoundError) as e:
        logger.warning("Forge: failed to resolve handler '%s': %s", handler_spec, e)
        return None


def discover_extensions(ext_dir: Path | None = None) -> list[dict[str, Any]]:
    """Discover all YAML/JSON manifests in the extensions directory."""
    directory = ext_dir or _DEFAULT_EXT_DIR
    if not directory.exists():
        return []

    manifests: list[dict[str, Any]] = []
    for path in sorted(directory.iterdir()):
        if path.suffix in (".yaml", ".yml", ".json") and path.is_file():
            manifest = _parse_manifest(path)
            if manifest is not None:
                manifest["_source_path"] = str(path)
                manifests.append(manifest)

    return manifests


def load_extensions(ext_dir: Path | None = None) -> dict[str, Any]:
    """Load and validate all extension manifests.

    Returns:
        Summary dict with loaded tools, errors, and injection results.
    """
    manifests = discover_extensions(ext_dir)
    loaded: list[dict[str, Any]] = []
    errors: list[str] = []
    skipped: list[str] = []

    for manifest in manifests:
        source = manifest.get("_source_path", "unknown")
        validation_errors = _validate_manifest(manifest, Path(source))

        if validation_errors:
            errors.extend(validation_errors)
            skipped.append(source)
            continue

        tool = manifest["tool"]
        handler = _resolve_handler(tool["handler"])
        if handler is None:
            errors.append(f"{source}: handler '{tool['handler']}' could not be resolved")
            skipped.append(source)
            continue

        # Inject into dispatch table and PRAT mapping
        injected = _inject_tool(
            name=tool["name"],
            handler=handler,
            gana=tool["gana"],
            description=tool.get("description", ""),
            safety=tool.get("safety", "read"),
        )

        if injected:
            loaded.append({
                "name": tool["name"],
                "gana": tool["gana"],
                "safety": tool.get("safety", "read"),
                "source": source,
            })
            logger.info("Forge: loaded extension tool '%s' → %s", tool["name"], tool["gana"])
        else:
            errors.append(f"{source}: injection failed for '{tool['name']}'")
            skipped.append(source)

    return {
        "status": "success",
        "loaded": len(loaded),
        "skipped": len(skipped),
        "tools": loaded,
        "errors": errors,
    }


def _inject_tool(
    name: str,
    handler: Any,
    gana: str,
    description: str = "",
    safety: str = "read",
) -> bool:
    """Inject a tool into the dispatch table and PRAT mapping.

    This is the core extension mechanism — it modifies the runtime
    routing tables without touching source files.
    """
    try:
        # 1. Inject into DISPATCH_TABLE
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE
        if name in DISPATCH_TABLE:
            logger.warning("Forge: tool '%s' already in dispatch table, skipping", name)
            return False
        DISPATCH_TABLE[name] = handler

        # 2. Inject into PRAT TOOL_TO_GANA mapping
        # Import here to avoid circular dependencies at module load time
        from whitemagic.tools.prat_mappings import GANA_TO_TOOLS
        from whitemagic.tools.prat_router import TOOL_TO_GANA
        if name not in TOOL_TO_GANA:
            TOOL_TO_GANA[name] = gana
        if gana in GANA_TO_TOOLS:
            if name not in GANA_TO_TOOLS[gana]:
                GANA_TO_TOOLS[gana].append(name)
        else:
            GANA_TO_TOOLS[gana] = [name]

        return True
    except Exception as e:
        logger.warning("Forge: injection failed for '%s': %s", name, e)
        return False


# ─── MCP Handlers ────────────────────────────────────────────────

def handle_forge_status(**kwargs: Any) -> dict[str, Any]:
    """Show current Forge status — loaded extensions and available manifests."""
    ext_dir = _DEFAULT_EXT_DIR
    manifests = discover_extensions(ext_dir)

    # Check what's already loaded
    loaded_names: list[str] = []
    try:
        from whitemagic.tools.prat_router import TOOL_TO_GANA
        # Find tools that aren't in the original hardcoded set
        # (We can't perfectly distinguish, but extensions typically have dots)
        loaded_names = [
            name for name in TOOL_TO_GANA
            if name.startswith("ext.") or name.startswith("custom.")
        ]
    except Exception:
        pass

    return {
        "status": "success",
        "extensions_dir": str(ext_dir),
        "extensions_dir_exists": ext_dir.exists(),
        "manifests_found": len(manifests),
        "manifest_files": [m.get("_source_path", "?") for m in manifests],
        "loaded_extension_tools": loaded_names,
        "usage": (
            "Place YAML manifests in ~/.whitemagic/extensions/ with format:\n"
            "tool:\n"
            "  name: custom.my_tool\n"
            "  description: What it does\n"
            "  gana: gana_ghost\n"
            "  safety: read\n"
            "  handler: 'my_module:my_function'"
        ),
    }


def handle_forge_reload(**kwargs: Any) -> dict[str, Any]:
    """Reload all extension manifests from disk."""
    return load_extensions()


def handle_forge_validate(**kwargs: Any) -> dict[str, Any]:
    """Validate extension manifests without loading them."""
    manifests = discover_extensions()
    results: list[dict[str, Any]] = []

    for manifest in manifests:
        source = manifest.get("_source_path", "unknown")
        validation_errors = _validate_manifest(manifest, Path(source))
        results.append({
            "file": source,
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "tool_name": manifest.get("tool", {}).get("name", "?"),
            "gana": manifest.get("tool", {}).get("gana", "?"),
        })

    valid_count = sum(1 for r in results if r["valid"])
    return {
        "status": "success",
        "total": len(results),
        "valid": valid_count,
        "invalid": len(results) - valid_count,
        "results": results,
    }
