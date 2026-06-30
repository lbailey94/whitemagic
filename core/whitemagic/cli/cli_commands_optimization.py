"""
CLI Commands: Optimization (G002)
=================================

wm skeleton <path>
"""

from pathlib import Path

import click

from whitemagic.optimization.skeletonizer import skeletonize_file


@click.group(name="opt")
def optimization_cli():
    """🚀 Optimization tools (Skeletonizer, etc.)"""
    pass


@optimization_cli.command(name="skeleton")
@click.argument("path", type=click.Path(exists=True))
@click.option("--output", "-o", help="Output file path (default: stdout)")
def skeleton_cmd(path, output):
    """Generate an AST skeleton for a file."""
    try:
        result = skeletonize_file(path)
        if output:
            Path(output).write_text(result, encoding="utf-8")
            click.echo(f"Skeleton written to {output}")
        else:
            click.echo(result)
    except (OSError, FileNotFoundError, PermissionError) as e:
        click.echo(f"Error: {e}", err=True)
