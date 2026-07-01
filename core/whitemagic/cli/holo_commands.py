# ruff: noqa: BLE001
"""
Holographic 4D Memory CLI Commands
===================================
Visualization and querying for the 4D memory space.

Phase 5: Added map, coords, constellation, and export commands.
"""

import json

import click

from whitemagic.core.memory.holographic import get_holographic_memory
from whitemagic.core.memory.unified import get_unified_memory


def ensure_initialized():
    """Ensure UnifiedMemory is initialized to populate the index"""
    get_unified_memory()


@click.group(name="holo")
def holo_cli():
    """🌌 Holographic 4D Memory Commands"""
    pass


@holo_cli.command(name="status")
def status():
    """Check holographic memory status"""
    ensure_initialized()
    holo = get_holographic_memory()
    stats = holo.get_stats()

    click.echo("\n🌌 Holographic Memory Status")
    click.echo("=" * 40)
    click.echo(f"Status: {stats.get('status', 'unknown')}")
    if stats.get("status") == "active":
        click.echo(f"Indexed Memories: {stats.get('count', 0)}")
    else:
        click.echo("⚠️  Rust backend required for holographic memory")


@holo_cli.command(name="query")
@click.argument("content")
@click.option("--limit", "-n", default=5, help="Number of results")
def query(content, limit):
    """Find nearest neighbors in 4D space"""
    ensure_initialized()
    holo = get_holographic_memory()
    if not holo._index:
        click.echo("❌ Holographic index not available")
        return

    # Create a dummy query dict to encode
    query_data = {"content": content, "tags": []}

    click.echo(f"\n🔎 Querying 4D Space: '{content}'")
    results = holo.query_nearest(query_data, k=limit)

    if not results:
        click.echo("No results found.")
        return

    unified = get_unified_memory()

    for i, res in enumerate(results, 1):
        mem = unified.recall(res.memory_id)
        if mem:
            preview = (
                str(mem.content)[:60] + "..."
                if len(str(mem.content)) > 60
                else str(mem.content)
            )
            click.echo(f"\n{i}. {preview}")
            click.echo(f"   ID: {res.memory_id} | Dist: {res.distance:.4f}")
            click.echo(f"   Type: {mem.memory_type.name} | Tags: {', '.join(mem.tags)}")
        else:
            click.echo(
                f"\n{i}. [Missing Memory {res.memory_id}] Dist: {res.distance:.4f}"
            )


@holo_cli.command(name="radius")
@click.argument("content")
@click.option("--radius", "-r", default=1.0, help="Search radius")
def radius(content, radius):
    """Find memories within a hypersphere radius"""
    ensure_initialized()
    holo = get_holographic_memory()
    if not holo._index:
        click.echo("❌ Holographic index not available")
        return

    query_data = {"content": content, "tags": []}

    click.echo(f"\n⭕ Radius Search (r={radius}): '{content}'")
    results = holo.query_radius(query_data, radius=radius)

    click.echo(f"Found {len(results)} memories in range.")

    unified = get_unified_memory()

    for i, res in enumerate(results[:10], 1):
        mem = unified.recall(res.memory_id)
        if mem:
            preview = (
                str(mem.content)[:60] + "..."
                if len(str(mem.content)) > 60
                else str(mem.content)
            )
            click.echo(f"  {i}. [{res.distance:.4f}] {preview}")




@holo_cli.command(name="map")
@click.option(
    "--axis",
    "-a",
    default="xy",
    type=click.Choice(["xy", "xz", "xw", "yz", "yw", "zw"]),
    help="Which 2D projection to show (default: xy = Logic/Emotion vs Micro/Macro)",
)
@click.option("--width", "-w", default=60, help="Map width in characters")
@click.option("--height", "-h", default=20, help="Map height in characters")
def map_view(axis, width, height):
    """📊 ASCII map of memories in 4D space (2D projection)

    Axes:
      x = Logic (-) ↔ Emotion (+)
      y = Micro (-) ↔ Macro (+)
      z = Past (-) ↔ Future (+)
      w = Importance (0 → 1)
    """
    ensure_initialized()
    unified = get_unified_memory()

    coords = unified.backend.get_all_coords()

    if not coords:
        click.echo("⚠️  No holographic coordinates found. Run reindex first.")
        return

    # Map axis names to indices
    axis_map = {"x": 0, "y": 1, "z": 2, "w": 3}
    axis1, axis2 = axis[0], axis[1]
    idx1, idx2 = axis_map[axis1], axis_map[axis2]

    axis_labels = {
        "x": "Logic ← → Emotion",
        "y": "Micro ← → Macro",
        "z": "Past ← → Future",
        "w": "Low ← → High Importance",
    }

    click.echo(f"\n🌌 HOLOGRAPHIC MEMORY MAP ({len(coords)} points)")
    click.echo(f"   X-Axis: {axis_labels[axis1]}")
    click.echo(f"   Y-Axis: {axis_labels[axis2]}")
    click.echo("=" * (width + 4))

    # Create ASCII grid
    grid = [[" " for _ in range(width)] for _ in range(height)]
    point_data = {}  # (row, col) -> memory_id

    for mem_id, (x, y, z, w) in coords.items():
        coord_tuple = (x, y, z, w)
        v1, v2 = coord_tuple[idx1], coord_tuple[idx2]

        # Normalize to grid coordinates (-1,1) -> (0, width/height)
        col = int((v1 + 1) / 2 * (width - 1))
        row = int((1 - (v2 + 1) / 2) * (height - 1))  # Invert y for display

        col = max(0, min(width - 1, col))
        row = max(0, min(height - 1, row))

        # Place marker based on importance (w)
        importance = coord_tuple[3]
        if importance > 0.8:
            marker = "★"
        elif importance > 0.5:
            marker = "●"
        else:
            marker = "·"

        grid[row][col] = marker
        point_data[(row, col)] = mem_id[:8]

    click.echo(f"  +{'-' * width}+")
    for row in grid:
        click.echo(f"  |{''.join(row)}|")
    click.echo(f"  +{'-' * width}+")

    # Legend
    click.echo("\n  Legend: ★ = high importance, ● = medium, · = low")
    click.echo(f"  Points: {len(coords)} memories mapped")


@holo_cli.command(name="coords")
@click.option("--limit", "-n", default=20, help="Number of memories to show")
@click.option(
    "--sort",
    "-s",
    default="importance",
    type=click.Choice(["importance", "time", "logic", "macro"]),
    help="Sort by axis",
)
def coords(limit, sort):
    """📍 List memory coordinates in 4D space"""
    ensure_initialized()
    unified = get_unified_memory()

    all_coords = unified.backend.get_all_coords()

    if not all_coords:
        click.echo("⚠️  No coordinates found.")
        return

    # Sort by specified axis
    sort_idx = {"logic": 0, "macro": 1, "time": 2, "importance": 3}[sort]
    sorted_items = sorted(
        all_coords.items(), key=lambda x: x[1][sort_idx], reverse=True
    )

    click.echo(f"\n📍 HOLOGRAPHIC COORDINATES (sorted by {sort})")
    click.echo("=" * 80)
    click.echo(
        f"{'ID':<12} {'X(Logic)':<10} {'Y(Macro)':<10} {'Z(Time)':<10} {'W(Importance)':<12} Title"
    )
    click.echo("-" * 80)

    for mem_id, (x, y, z, w) in sorted_items[:limit]:
        mem = unified.recall(mem_id)
        title = (mem.title or str(mem.content)[:20]) if mem else "[deleted]"
        title = title[:25] + "..." if len(title) > 25 else title
        click.echo(
            f"{mem_id[:10]:<12} {x:>+8.3f}  {y:>+8.3f}  {z:>+8.3f}  {w:>10.3f}    {title}"
        )

    if len(all_coords) > limit:
        click.echo(f"\n... and {len(all_coords) - limit} more memories")


@holo_cli.command(name="constellation")
@click.argument("query")
@click.option("--radius", "-r", default=0.5, help="Search radius in 4D space")
@click.option("--limit", "-n", default=10, help="Max results")
def constellation(query, radius, limit):
    """✨ Find a constellation of related memories around a concept

    Uses spatial proximity in 4D holographic space to find memories
    that share similar characteristics (logic/emotion, scale, time, importance).
    """
    ensure_initialized()

    try:
        from whitemagic.core.intelligence.multi_spectral_reasoning import get_reasoner

        reasoner = get_reasoner()

        click.echo(f"\n✨ CONSTELLATION SEARCH: '{query}'")
        click.echo(f"   Radius: {radius} | Max: {limit}")
        click.echo("=" * 60)

        results = reasoner.find_constellation(query, radius=radius, limit=limit)

        if not results:
            click.echo("No memories found in constellation radius.")
            click.echo("Try increasing --radius or check that memories are indexed.")
            return

        click.echo(f"\n🌟 Found {len(results)} memories in constellation:\n")

        for i, mem in enumerate(results, 1):
            dist_bar = "█" * int((1 - mem["distance"]) * 10) + "░" * int(
                mem["distance"] * 10
            )
            click.echo(f"{i}. [{dist_bar}] {mem['title']}")
            click.echo(
                f"   Distance: {mem['distance']:.4f} | Importance: {mem['importance']:.2f}"
            )
            click.echo(
                f"   Tags: {', '.join(mem['tags'][:5]) if mem['tags'] else 'none'}"
            )
            click.echo(f"   Preview: {mem['content'][:80]}...")
            click.echo()

    except Exception as e:
        click.echo(f"❌ Constellation search failed: {e}")


@holo_cli.command(name="export")
@click.argument("output", type=click.Path())
@click.option(
    "--format",
    "-f",
    default="json",
    type=click.Choice(["json", "csv"]),
    help="Export format",
)
def export(output, format):
    """📤 Export holographic coordinates for external visualization

    Exports all memory coordinates to JSON or CSV for use with
    external 3D/4D visualization tools (e.g., Three.js, Plotly).
    """
    ensure_initialized()
    unified = get_unified_memory()

    all_coords = unified.backend.get_all_coords()

    if not all_coords:
        click.echo("⚠️  No coordinates to export.")
        return

    # Build export data with full memory info
    export_data = []
    for mem_id, (x, y, z, w) in all_coords.items():
        mem = unified.recall(mem_id)
        entry = {
            "id": mem_id,
            "x": x,
            "y": y,
            "z": z,
            "w": w,
            "title": mem.title if mem else None,
            "type": mem.memory_type.name if mem else None,
            "tags": list(mem.tags) if mem else [],
            "content_preview": str(mem.content)[:100] if mem else None,
        }
        export_data.append(entry)

    if format == "json":
        with open(output, "w") as f:
            json.dump(
                {
                    "axis_definitions": {
                        "x": "Logic (-1) to Emotion (+1)",
                        "y": "Micro (-1) to Macro (+1)",
                        "z": "Past (-1) to Future (+1)",
                        "w": "Importance (0 to 1)",
                    },
                    "point_count": len(export_data),
                    "points": export_data,
                },
                f,
                indent=2,
            )
    else:  # CSV
        with open(output, "w") as f:
            f.write("id,x,y,z,w,title,type,tags\n")
            for entry in export_data:
                tags_str = "|".join(entry["tags"])
                title = (entry["title"] or "").replace(",", ";")
                f.write(
                    f"{entry['id']},{entry['x']:.4f},{entry['y']:.4f},{entry['z']:.4f},{entry['w']:.4f},{title},{entry['type']},{tags_str}\n"
                )

    click.echo(f"✅ Exported {len(export_data)} points to {output}")


@holo_cli.command(name="sectors")
def sectors():
    """🗺️  Show memory distribution across semantic sectors

    Divides the 4D space into named sectors and shows memory counts.
    """
    ensure_initialized()
    unified = get_unified_memory()

    all_coords = unified.backend.get_all_coords()

    if not all_coords:
        click.echo("⚠️  No coordinates found.")
        return

    # Define semantic sectors
    sector_counts = {
        "🧠 Logical/Micro (analytical details)": 0,
        "💭 Logical/Macro (strategic plans)": 0,
        "💗 Emotional/Micro (personal moments)": 0,
        "🌟 Emotional/Macro (big picture feelings)": 0,
        "⭐ High Importance": 0,
        "📍 Low Importance": 0,
        "🕐 Past-focused": 0,
        "🔮 Future-focused": 0,
    }

    for mem_id, (x, y, z, w) in all_coords.items():
        # X-Y quadrants
        if x < 0 and y < 0:
            sector_counts["🧠 Logical/Micro (analytical details)"] += 1
        elif x < 0 and y >= 0:
            sector_counts["💭 Logical/Macro (strategic plans)"] += 1
        elif x >= 0 and y < 0:
            sector_counts["💗 Emotional/Micro (personal moments)"] += 1
        else:
            sector_counts["🌟 Emotional/Macro (big picture feelings)"] += 1

        # Importance
        if w > 0.7:
            sector_counts["⭐ High Importance"] += 1
        elif w < 0.3:
            sector_counts["📍 Low Importance"] += 1

        # Time
        if z < -0.3:
            sector_counts["🕐 Past-focused"] += 1
        elif z > 0.3:
            sector_counts["🔮 Future-focused"] += 1

    click.echo(f"\n🗺️  SEMANTIC SECTOR DISTRIBUTION ({len(all_coords)} total)")
    click.echo("=" * 50)

    for sector, count in sector_counts.items():
        pct = count / len(all_coords) * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        click.echo(f"{sector:<45} {bar} {count:>3} ({pct:.0f}%)")


# === DHARMA DASHBOARD COMMAND ===


@holo_cli.command(name="dharma")
@click.option("--limit", "-n", default=10, help="Number of audit entries to show")
def dharma_dashboard(limit: int):
    """Show Dharma ethics audit dashboard."""
    from whitemagic.core.memory.unified import get_unified_memory

    click.echo("╭─────────────────────────────────────────╮")
    click.echo("│        🕉️  DHARMA AUDIT DASHBOARD        │")
    click.echo("╰─────────────────────────────────────────╯")
    click.echo()

    unified = get_unified_memory()

    try:
        stats = unified.backend.get_dharma_stats()
        click.echo("📊 STATISTICS:")
        click.echo(f"   Total audits: {stats.get('total', 0)}")
        click.echo(f"   Avg ethical score: {stats.get('avg_ethical', 0):.2f}")
        click.echo(f"   Avg harmony score: {stats.get('avg_harmony', 0):.2f}")
        click.echo()
    except Exception as e:
        click.echo(f"   (No stats available: {e})")
        click.echo()

    try:
        log = unified.backend.get_dharma_audit_log(limit=limit)
        if log:
            click.echo(f"📜 RECENT AUDITS (last {len(log)}):")
            click.echo("─" * 60)
            for entry in log:
                ts = entry.get("timestamp", "N/A")[:19]
                action = entry.get("action", "unknown")[:30]
                eth = entry.get("ethical_score", 0)
                harm = entry.get("harmony_score", 0)
                decision = entry.get("decision", "N/A")

                # Color code by ethical score
                if eth >= 0.8:
                    status = "✅"
                elif eth >= 0.5:
                    status = "⚠️"
                else:
                    status = "❌"

                click.echo(f"{status} [{ts}] {action:<30}")
                click.echo(
                    f"   Ethics: {eth:.2f} | Harmony: {harm:.2f} | Decision: {decision}"
                )
        else:
            click.echo("   No audit entries yet.")
    except Exception as e:
        click.echo(f"   Error loading audit log: {e}")

    click.echo()
    click.echo("─" * 60)
    click.echo("Use 'whitemagic holo dharma -n 20' for more entries")
