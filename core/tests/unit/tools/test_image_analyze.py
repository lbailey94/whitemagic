"""Unit tests for image_analyze tool handler."""
import os
import tempfile

import pytest
from PIL import Image, ImageDraw


def _make_test_image(path: str, text_lines: list[str] | None = None) -> str:
    """Create a simple test image with optional text-like horizontal lines."""
    img = Image.new("RGBA", (200, 200), (255, 255, 255, 255))
    if text_lines:
        draw = ImageDraw.Draw(img)
        for i, line in enumerate(text_lines):
            y = 20 + i * 30
            draw.text((10, y), line, fill=(0, 0, 0, 255))
    img.save(path, format="PNG")
    return path


class TestImageAnalyzeHandler:
    """Tests for handle_image_analyze."""

    def test_missing_params_returns_error(self):
        from whitemagic.tools.handlers.image_tools import handle_image_analyze

        result = handle_image_analyze()
        assert result["status"] == "error"
        assert result["error_code"] == "invalid_params"

    def test_file_not_found_returns_error(self):
        from whitemagic.tools.handlers.image_tools import handle_image_analyze

        result = handle_image_analyze(image_path="/nonexistent/image.png")
        assert result["status"] == "error"
        assert result["error_code"] == "file_not_found"

    def test_structural_analysis_blank_image(self):
        from whitemagic.tools.handlers.image_tools import handle_image_analyze

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            _make_test_image(tmp.name)
            result = handle_image_analyze(
                image_path=tmp.name,
                extract_text=False,
            )
            os.unlink(tmp.name)

        assert result["status"] == "success"
        assert result["metadata"]["format"] == "PNG"
        assert result["structure"]["dimensions"] == {"width": 200, "height": 200}
        assert result["structure"]["text_band_count"] == 0
        assert result["ocr"]["text"] is None

    def test_structural_analysis_with_content(self):
        from whitemagic.tools.handlers.image_tools import handle_image_analyze

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            _make_test_image(tmp.name, text_lines=["Hello World", "Test Line 2"])
            result = handle_image_analyze(
                image_path=tmp.name,
                extract_text=False,
            )
            os.unlink(tmp.name)

        assert result["status"] == "success"
        assert result["structure"]["text_band_count"] > 0
        assert result["structure"]["tonal_distribution"]["light_pct"] > 90
        assert len(result["structure"]["dominant_colors"]) > 0

    def test_grid_layout_is_list_of_strings(self):
        from whitemagic.tools.handlers.image_tools import handle_image_analyze

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            _make_test_image(tmp.name, text_lines=["Test"])
            result = handle_image_analyze(
                image_path=tmp.name,
                extract_text=False,
            )
            os.unlink(tmp.name)

        grid = result["structure"]["grid_layout"]
        assert isinstance(grid, list)
        assert all(isinstance(row, str) for row in grid)
        assert len(grid) == 12

    def test_metadata_extraction(self):
        from whitemagic.tools.handlers.image_tools import handle_image_analyze

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            _make_test_image(tmp.name)
            result = handle_image_analyze(
                image_path=tmp.name,
                extract_text=False,
            )
            os.unlink(tmp.name)

        meta = result["metadata"]
        assert meta["format"] == "PNG"
        assert meta["file_size_bytes"] > 0
        assert result["structure"]["dimensions"]["width"] == 200
        assert result["structure"]["dimensions"]["height"] == 200


class TestImageAnalyzeRegistry:
    """Tests for registry and dispatch table integration."""

    def test_tool_in_registry(self):
        from whitemagic.tools.registry_defs.browser import BROWSER_TOOLS

        names = [t.name for t in BROWSER_TOOLS]
        assert "image_analyze" in names

    def test_tool_in_dispatch_table(self):
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        assert "image_analyze" in DISPATCH_TABLE

    def test_prat_mapping_to_chariot(self):
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA

        assert TOOL_TO_GANA.get("image_analyze") == "gana_chariot"
