from datetime import datetime
from pathlib import Path

import click

__all__ = ["galaxy_command", "backup_command", "restore_command"]


@click.command(name="galaxy")
def galaxy_command() -> None:
    """Launch the Galaxy TUI (Visual Memory Browser)"""
    try:
        from whitemagic.interfaces.tui import GalaxyTUI

        # Run the TUI
        app = GalaxyTUI()
        app.run()
    except ImportError as e:
        click.echo(
            f"❌ Error: TUI dependencies missing. Install with 'pip install whitemagic[tui]' ({e})"
        )
    except (ImportError, ModuleNotFoundError) as e:
        click.echo(f"❌ Error launching Galaxy: {e}")


@click.command(name="backup")
@click.option("--output", "-o", default=None, help="Output path for backup archive")
@click.option("--galaxy", default=None, help="Backup a specific galaxy (default: all)")
def backup_command(output: str | None, galaxy: str | None) -> None:
    """📦 Backup WhiteMagic memory databases.

    Creates a timestamped .tar.gz archive of the memory directory.
    """
    import tarfile

    from whitemagic.config import paths as cfg_paths

    state_root = cfg_paths.get_state_root()  # type: ignore[attr-defined]
    memory_dir = state_root / "memory"

    if not memory_dir.exists():
        click.echo("❌ No memory directory found. Nothing to backup.")
        raise SystemExit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output:
        out_path = Path(output)
    else:
        out_path = Path.cwd() / f"whitemagic_backup_{timestamp}.tar.gz"

    if galaxy:
        # Backup specific galaxy
        galaxy_dir = memory_dir / "galaxies" / galaxy
        if not galaxy_dir.exists():
            click.echo(f"❌ Galaxy '{galaxy}' not found at {galaxy_dir}")
            raise SystemExit(1)
        source = galaxy_dir
        label = f"galaxy:{galaxy}"
    else:
        source = memory_dir
        label = "all memories"

    click.echo(f"📦 Backing up {label} from {source}")
    try:
        with tarfile.open(str(out_path), "w:gz") as tar:
            tar.add(str(source), arcname=source.name)
        size_mb = out_path.stat().st_size / (1024 * 1024)
        click.echo(f"✅ Backup saved: {out_path} ({size_mb:.1f} MB)")
    except (OSError, FileNotFoundError, PermissionError) as e:
        click.echo(f"❌ Backup failed: {e}")
        raise SystemExit(1)


@click.command(name="restore")
@click.argument("archive_path")
@click.option("--force", is_flag=True, help="Overwrite existing data")
def restore_command(archive_path: str, force: bool) -> None:
    """📦 Restore WhiteMagic memory from a backup archive."""
    import tarfile

    from whitemagic.config import paths as cfg_paths

    archive = Path(archive_path)
    if not archive.exists():
        click.echo(f"❌ Archive not found: {archive}")
        raise SystemExit(1)

    state_root = cfg_paths.get_state_root()  # type: ignore[attr-defined]
    memory_dir = state_root / "memory"

    if memory_dir.exists() and not force:
        click.echo("❌ Memory directory already exists. Use --force to overwrite.")
        raise SystemExit(1)

    click.echo(f"📦 Restoring from {archive}")
    try:
        memory_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(str(archive), "r:gz") as tar:
            tar.extractall(str(memory_dir.parent))
        click.echo(f"✅ Restored to {memory_dir}")
    except (OSError, FileNotFoundError, PermissionError) as e:
        click.echo(f"❌ Restore failed: {e}")
        raise SystemExit(1)
