"""Image analysis tool handlers — OCR, structural analysis, and metadata extraction.

Provides the `image_analyze` tool for gana_chariot. Uses a tiered approach:
1. Tesseract OCR (if installed) — best text extraction
2. Online OCR API (ocr.space) — fallback for text extraction
3. PIL-based structural analysis — always available, detects layout/content regions

Returns a stable JSON envelope with metadata, structural analysis, and OCR text.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Any
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_OCR_API_KEY = "K87897627788957"
_OCR_API_URL = "https://api.ocr.space/parse/image"


def _emit(event_type: str, data: dict[str, Any]) -> None:
    from whitemagic.tools.unified_api import _emit_gan_ying

    _emit_gan_ying(event_type, data)


def _has_tesseract() -> bool:
    """Check if tesseract binary is available on the system."""
    return shutil.which("tesseract") is not None


def _tesseract_ocr(image_path: str) -> tuple[str | None, str | None]:
    """Run tesseract OCR on an image file.

    Returns (text, error). If tesseract is not installed, returns (None, None).
    """
    if not _has_tesseract():
        return None, None
    try:
        result = subprocess.run(
            ["tesseract", image_path, "-", "--psm", "6"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout.strip(), None
        return None, result.stderr.strip()
    except Exception as e:
        logger.warning("tesseract OCR failed: %s", e)
        return None, str(e)


def _online_ocr(image_path: str) -> tuple[str | None, str | None]:
    """Use the ocr.space free API as a fallback OCR method.

    Returns (text, error). If the API is unreachable, returns (None, error).
    """
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()

        # Build multipart form data manually (avoid adding requests dependency)
        boundary = "----WMImageAnalyzeBoundary"
        body = b""
        body += f"--{boundary}\r\n".encode()
        body += b'Content-Disposition: form-data; name="apikey"\r\n\r\n'
        body += f"{_OCR_API_KEY}\r\n".encode()
        body += f"--{boundary}\r\n".encode()
        body += b'Content-Disposition: form-data; name="language"\r\n\r\n'
        body += b"eng\r\n"
        body += f"--{boundary}\r\n".encode()
        body += b'Content-Disposition: form-data; name="isOverlayRequired"\r\n\r\n'
        body += b"false\r\n"
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(image_path)}"\r\n'.encode()
        body += b"Content-Type: image/png\r\n\r\n"
        body += image_data
        body += f"\r\n--{boundary}--\r\n".encode()

        req = Request(
            _OCR_API_URL,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            if data.get("ParsedResults"):
                return data["ParsedResults"][0].get("ParsedText", "").strip(), None
            return None, data.get("ErrorMessage", "No OCR results")
    except Exception as e:
        logger.warning("online OCR failed: %s", e)
        return None, str(e)


def _structural_analysis(img: Any) -> dict[str, Any]:
    """Analyze image structure using PIL — layout, content regions, colors.

    Args:
        img: PIL Image (already opened, converted to RGBA)

    Returns:
        Dict with dimensions, content bounding box, grid layout, text bands,
        tonal distribution, and dominant colors.
    """
    from PIL import Image

    w, h = img.size
    bg = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    composite = Image.alpha_composite(bg, img).convert("L")
    pixels = composite.load()

    # Content bounding box
    min_x, min_y, max_x, max_y = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            if pixels[x, y] < 240:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    has_content = max_x > min_x
    bbox = (min_x, min_y, max_x, max_y) if has_content else None
    content_w = (max_x - min_x) if has_content else 0
    content_h = (max_y - min_y) if has_content else 0

    # Tonal distribution
    hist = composite.histogram()
    total = sum(hist) or 1
    dark_pct = round(sum(hist[:85]) / total * 100, 1)
    mid_pct = round(sum(hist[85:170]) / total * 100, 1)
    light_pct = round(sum(hist[170:]) / total * 100, 1)

    # Grid layout (12x12)
    grid_cols, grid_rows = 12, 12
    cell_w = max(1, w // grid_cols)
    cell_h = max(1, h // grid_rows)
    grid = []
    for gy in range(grid_rows):
        row = []
        for gx in range(grid_cols):
            x0 = gx * cell_w
            y0 = gy * cell_h
            cell = composite.crop((x0, y0, x0 + cell_w, y0 + cell_h))
            cell_hist = cell.histogram()
            cell_total = sum(cell_hist) or 1
            dark = sum(cell_hist[:200]) / cell_total * 100
            if dark > 1:
                row.append("#")
            elif dark > 0.1:
                row.append(".")
            else:
                row.append(" ")
        grid.append("".join(row))

    # Detect horizontal content bands (text rows)
    row_densities = []
    for y in range(h):
        row_dark = sum(1 for x in range(w) if pixels[x, y] < 200)
        row_densities.append(row_dark)

    text_bands = []
    in_band = False
    band_start = 0
    for y in range(h):
        if row_densities[y] > 2:
            if not in_band:
                band_start = y
                in_band = True
        else:
            if in_band:
                band_height = y - band_start
                avg_density = round(
                    sum(row_densities[band_start:y]) / max(1, band_height), 1
                )
                band_type = (
                    "thick"
                    if band_height > 20
                    else "thin"
                    if band_height > 5
                    else "line"
                )
                text_bands.append(
                    {
                        "y_start": band_start,
                        "y_end": y - 1,
                        "height": band_height,
                        "avg_density": avg_density,
                        "type": band_type,
                    }
                )
                in_band = False
    if in_band:
        band_height = h - band_start
        avg_density = round(sum(row_densities[band_start:h]) / max(1, band_height), 1)
        text_bands.append(
            {
                "y_start": band_start,
                "y_end": h - 1,
                "height": band_height,
                "avg_density": avg_density,
                "type": "thick" if band_height > 20 else "thin",
            }
        )

    # Dominant colors (sampled from 50x50 downscale)
    small = img.convert("RGB").resize((50, 50))
    colors = small.getcolors(2500)
    top_colors = []
    if colors:
        colors.sort(key=lambda c: c[0], reverse=True)
        top_colors = [{"count": c[0], "rgb": list(c[1])} for c in colors[:5]]

    return {
        "dimensions": {"width": w, "height": h},
        "content_bounding_box": bbox,
        "content_coverage_pct": round((content_w * content_h) / (w * h) * 100, 1)
        if has_content
        else 0,
        "tonal_distribution": {
            "dark_pct": dark_pct,
            "mid_pct": mid_pct,
            "light_pct": light_pct,
        },
        "grid_layout": grid,
        "text_bands": text_bands,
        "text_band_count": len(text_bands),
        "dominant_colors": top_colors,
    }


def _download_image(url: str) -> str:
    """Download an image from a URL to a temporary file."""
    req = Request(url, headers={"User-Agent": "WhiteMagic-ImageAnalyze/1.0"})
    with urlopen(req, timeout=15) as resp:
        data = resp.read()
    suffix = ".png"
    if "content-type" in resp.headers:
        ct = resp.headers["content-type"].lower()
        if "jpeg" in ct or "jpg" in ct:
            suffix = ".jpg"
        elif "webp" in ct:
            suffix = ".webp"
        elif "gif" in ct:
            suffix = ".gif"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(data)
    tmp.close()
    return tmp.name


def handle_image_analyze(**kwargs: Any) -> dict[str, Any]:
    """Analyze an image file: extract metadata, structural layout, and OCR text.

    Tiered OCR approach:
    1. Tesseract (if installed locally)
    2. ocr.space API (online fallback)
    3. PIL structural analysis (always available)

    Args (via kwargs):
        image_path: Path to local image file (required if no url)
        url: URL of image to analyze (required if no image_path)
        extract_text: Whether to attempt OCR (default True)
        max_text_length: Maximum OCR text length to return (default 5000)

    Returns:
        Stable JSON envelope with metadata, structural analysis, and OCR text.
    """
    from PIL import Image

    image_path = kwargs.get("image_path", "")
    url = kwargs.get("url", "")
    extract_text = kwargs.get("extract_text", True)
    max_text_length = int(kwargs.get("max_text_length", 5000))

    if not image_path and not url:
        return {
            "status": "error",
            "error_code": "invalid_params",
            "message": "Either image_path or url is required",
        }

    tmp_path = None
    try:
        # Resolve image source
        if url and not image_path:
            try:
                image_path = _download_image(url)
                tmp_path = image_path
            except Exception as e:
                return {
                    "status": "error",
                    "error_code": "fetch_failed",
                    "message": f"Failed to download image: {e}",
                }

        if not os.path.exists(image_path):
            return {
                "status": "error",
                "error_code": "file_not_found",
                "message": f"Image file not found: {image_path}",
            }

        # Open image
        try:
            img = Image.open(image_path)
        except Exception as e:
            return {
                "status": "error",
                "error_code": "invalid_image",
                "message": f"Cannot open image: {e}",
            }

        # Convert to RGBA for consistent processing
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        # File metadata
        file_size = os.path.getsize(image_path)
        metadata = {
            "file_path": image_path,
            "file_size_bytes": file_size,
            "format": img.format or "unknown",
            "mode": img.mode,
            "software": img.info.get("Software"),
            "creation_time": img.info.get("Creation Time"),
        }

        # Structural analysis (always available)
        structure = _structural_analysis(img)

        # OCR (tiered)
        ocr_result: dict[str, Any] = {
            "text": None,
            "method": None,
            "error": None,
        }

        if extract_text:
            # Convert to grayscale PNG for OCR engines
            gray_path = None
            try:
                bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
                composite = Image.alpha_composite(bg, img).convert("L")
                gray_tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                composite.save(gray_tmp, format="PNG")
                gray_tmp.close()
                gray_path = gray_tmp.name

                # Tier 1: Tesseract
                text, err = _tesseract_ocr(gray_path)
                if text:
                    ocr_result = {
                        "text": text[:max_text_length],
                        "method": "tesseract",
                        "error": None,
                    }
                else:
                    # Tier 2: Online OCR
                    text, err = _online_ocr(gray_path)
                    if text:
                        ocr_result = {
                            "text": text[:max_text_length],
                            "method": "ocr_space_api",
                            "error": None,
                        }
                    else:
                        ocr_result = {
                            "text": None,
                            "method": None,
                            "error": err or "All OCR methods failed",
                        }
            finally:
                if gray_path and os.path.exists(gray_path):
                    os.unlink(gray_path)

        result = {
            "metadata": metadata,
            "structure": structure,
            "ocr": ocr_result,
        }

        _emit(
            "IMAGE_ANALYZE",
            {
                "image": os.path.basename(image_path),
                "ocr_method": ocr_result.get("method"),
                "text_length": len(ocr_result.get("text") or ""),
                "bands": structure["text_band_count"],
            },
        )

        return {"status": "success", **result}

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
