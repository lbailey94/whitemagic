from pathlib import Path
from typing import Any, Dict

__all__ = ["load_config"]


def load_config(project_path: Path) -> Dict[str, Any]:
    """Load [tool.strata] section from pyproject.toml if present."""
    config_path = project_path / "pyproject.toml"
    if not config_path.exists():
        return {}
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            return {}
    try:
        with config_path.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, ValueError):
        return {}
    return data.get("tool", {}).get("strata", {})
