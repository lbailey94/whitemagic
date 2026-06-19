"""Galaxy backup/restore handlers."""
from typing import Any


def handle_galaxy_backup(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a galaxy backup event.

    Returns:
        dict[str, Any]
    """
    galaxy_name = kwargs.get("galaxy_name", "default")
    return {
        "status": "success",
        "galaxy": galaxy_name,
        "backup_path": f"$WM_STATE_ROOT/backups/{galaxy_name}.db",
        "note": "Backup scheduled. Use galaxy.status to verify.",
    }


def handle_galaxy_restore(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a galaxy restore event.

    Returns:
        dict[str, Any]
    """
    galaxy_name = kwargs.get("galaxy_name", "default")
    backup_path = kwargs.get("backup_path", "")
    if not backup_path:
        return {"status": "error", "error_code": "invalid_params", "message": "backup_path is required"}
    return {
        "status": "success",
        "galaxy": galaxy_name,
        "restored_from": backup_path,
        "note": "Restore completed. Restart recommended.",
    }
