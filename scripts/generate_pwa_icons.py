#!/usr/bin/env python3
"""Generate PWA icons for WhiteMagic dashboard.

Creates SVG icons and converts them to PNG using CairoSVG.

Usage:
    python scripts/generate_pwa_icons.py
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    import cairosvg
    HAS_CAIROSVG = True
except ImportError:
    HAS_CAIROSVG = False

# PWA icon sizes
ICON_SIZES = [
    (192, 192),
    (512, 512),
    (144, 144),
    (96, 96),
    (72, 72),
    (48, 48),
]

# Apple touch icon sizes
APPLE_SIZES = [
    (180, 180),  # iPhone 120pt @ 3x
    (152, 152),  # iPad 76pt @ 2x
    (120, 120),  # iPhone 60pt @ 2x
    (76, 76),    # iPad 76pt @ 1x
    (60, 60),    # iPhone 60pt @ 1x
]

# Favicon sizes
FAVICON_SIZES = [
    (32, 32),
    (16, 16),
]


def generate_icon_svg(size: int) -> str:
    """Generate an SVG icon for the given size."""
    # Colors
    bg_primary = "#0a0a1a"
    bg_gradient_start = "#1a1a3e"
    bg_gradient_end = "#0a0a1a"
    star_color = "#7c3aed"
    star_glow = "#a78bfa"
    accent_color = "#06b6d4"
    accent_glow = "#67e8f9"
    core_color = "#f59e0b"

    # Calculate positions based on size
    center = size / 2
    outer_radius = size * 0.35
    inner_radius = size * 0.15
    core_radius = size * 0.06

    # Generate star points (5-pointed star)
    star_points = []
    for i in range(10):
        angle = (i * 36 - 90) * 3.14159 / 180
        r = outer_radius if i % 2 == 0 else inner_radius
        x = center + r * 0.8 * (0.5 + 0.5 * (i % 2))  # Slightly elliptical
        y = center + r * (0.5 + 0.5 * ((i + 1) % 2))
        star_points.append(f"{x:.1f},{y:.1f}")

    # Generate orbit rings
    orbits = []
    for i in range(3):
        rx = outer_radius * (0.6 + i * 0.25)
        ry = outer_radius * (0.3 + i * 0.15)
        rotation = i * 30
        orbits.append((rx, ry, rotation))

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">
  <defs>
    <radialGradient id="bg" cx="50%" cy="50%" r="70%">
      <stop offset="0%" stop-color="{bg_gradient_start}"/>
      <stop offset="100%" stop-color="{bg_gradient_end}"/>
    </radialGradient>
    <radialGradient id="glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{star_glow}" stop-opacity="0.6"/>
      <stop offset="100%" stop-color="{star_glow}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="coreGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{core_color}" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="{core_color}" stop-opacity="0"/>
    </radialGradient>
    <filter id="blur">
      <feGaussianBlur stdDeviation="{size * 0.02}"/>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="{size}" height="{size}" rx="{size * 0.15}" fill="url(#bg)"/>

  <!-- Orbit rings -->
  <ellipse cx="{center}" cy="{center}" rx="{orbits[0][0]}" ry="{orbits[0][1]}"
           fill="none" stroke="{accent_color}" stroke-width="{size * 0.008}"
           opacity="0.4" transform="rotate({orbits[0][2]} {center} {center})"/>
  <ellipse cx="{center}" cy="{center}" rx="{orbits[1][0]}" ry="{orbits[1][1]}"
           fill="none" stroke="{star_color}" stroke-width="{size * 0.006}"
           opacity="0.3" transform="rotate({orbits[1][2]} {center} {center})"/>
  <ellipse cx="{center}" cy="{center}" rx="{orbits[2][0]}" ry="{orbits[2][1]}"
           fill="none" stroke="{accent_glow}" stroke-width="{size * 0.004}"
           opacity="0.2" transform="rotate({orbits[2][2]} {center} {center})"/>

  <!-- Star glow -->
  <circle cx="{center}" cy="{center}" r="{outer_radius * 1.2}" fill="url(#glow)"/>

  <!-- 5-pointed star (holographic symbol) -->
  <polygon points="{" ".join(star_points)}"
           fill="{star_color}" opacity="0.9"/>

  <!-- Core glow -->
  <circle cx="{center}" cy="{center}" r="{core_radius * 3}" fill="url(#coreGlow)"/>

  <!-- Core dot -->
  <circle cx="{center}" cy="{center}" r="{core_radius}" fill="{core_color}"/>

  <!-- Accent dots (representing 5D coordinates) -->
  <circle cx="{center - outer_radius * 0.5}" cy="{center - outer_radius * 0.3}"
          r="{size * 0.02}" fill="{accent_color}" opacity="0.7"/>
  <circle cx="{center + outer_radius * 0.4}" cy="{center - outer_radius * 0.5}"
          r="{size * 0.015}" fill="{accent_glow}" opacity="0.6"/>
  <circle cx="{center + outer_radius * 0.6}" cy="{center + outer_radius * 0.2}"
          r="{size * 0.018}" fill="{star_glow}" opacity="0.5"/>
</svg>'''

    return svg


def generate_favicon_svg(size: int) -> str:
    """Generate a simplified favicon SVG."""
    center = size / 2
    radius = size * 0.35
    core_radius = size * 0.12

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">
  <rect width="{size}" height="{size}" fill="#0a0a1a"/>
  <circle cx="{center}" cy="{center}" r="{radius}" fill="#7c3aed" opacity="0.8"/>
  <circle cx="{center}" cy="{center}" r="{core_radius}" fill="#f59e0b"/>
</svg>'''

    return svg


def main():
    output_dir = Path(__file__).resolve().parent.parent / "apps" / "site" / "public" / "icons"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating PWA icons in {output_dir}")

    all_files = []

    # Generate main icons
    for width, height in ICON_SIZES:
        svg = generate_icon_svg(width)
        svg_filename = f"icon-{width}x{height}.svg"
        (output_dir / svg_filename).write_text(svg)
        all_files.append(svg_filename)

        if HAS_CAIROSVG:
            png_filename = f"icon-{width}x{height}.png"
            cairosvg.svg2svg(bytestring=svg.encode(), write_to=str(output_dir / svg_filename))
            cairosvg.svg2png(bytestring=svg.encode(), write_to=str(output_dir / png_filename))
            all_files.append(png_filename)
            print(f"  Created {svg_filename} + {png_filename}")
        else:
            print(f"  Created {svg_filename} (SVG only)")

    # Generate Apple touch icons
    for width, height in APPLE_SIZES:
        svg = generate_icon_svg(width)
        svg_filename = f"apple-touch-icon-{width}x{height}.svg"
        (output_dir / svg_filename).write_text(svg)
        all_files.append(svg_filename)

        if HAS_CAIROSVG:
            png_filename = f"apple-touch-icon-{width}x{height}.png"
            cairosvg.svg2png(bytestring=svg.encode(), write_to=str(output_dir / png_filename))
            all_files.append(png_filename)
            print(f"  Created {svg_filename} + {png_filename}")
        else:
            print(f"  Created {svg_filename} (SVG only)")

    # Generate default apple-touch-icon
    apple_svg = generate_icon_svg(180)
    (output_dir / "apple-touch-icon.svg").write_text(apple_svg)
    if HAS_CAIROSVG:
        cairosvg.svg2png(bytestring=apple_svg.encode(), write_to=str(output_dir / "apple-touch-icon.png"))
        print("  Created apple-touch-icon.svg + apple-touch-icon.png")
    else:
        print("  Created apple-touch-icon.svg")

    # Generate favicons
    for width, height in FAVICON_SIZES:
        svg = generate_favicon_svg(width)
        svg_filename = f"favicon-{width}x{height}.svg"
        (output_dir / svg_filename).write_text(svg)
        all_files.append(svg_filename)

        if HAS_CAIROSVG:
            png_filename = f"favicon-{width}x{height}.png"
            cairosvg.svg2png(bytestring=svg.encode(), write_to=str(output_dir / png_filename))
            all_files.append(png_filename)
            print(f"  Created {svg_filename} + {png_filename}")
        else:
            print(f"  Created {svg_filename} (SVG only)")

    # Generate default favicon
    favicon_svg = generate_favicon_svg(32)
    (output_dir / "favicon.svg").write_text(favicon_svg)
    if HAS_CAIROSVG:
        cairosvg.svg2png(bytestring=favicon_svg.encode(), write_to=str(output_dir / "favicon.png"))
        print("  Created favicon.svg + favicon.png")
    else:
        print("  Created favicon.svg")

    # Generate manifest icon reference (512x512)
    manifest_svg = generate_icon_svg(512)
    (output_dir / "icon-512x512.svg").write_text(manifest_svg)
    if HAS_CAIROSVG:
        cairosvg.svg2png(bytestring=manifest_svg.encode(), write_to=str(output_dir / "icon-512x512.png"))
        print("  Created icon-512x512.svg + icon-512x512.png (manifest)")
    else:
        print("  Created icon-512x512.svg (manifest)")

    print(f"\nGenerated {len(all_files)} icon files")


if __name__ == "__main__":
    main()
