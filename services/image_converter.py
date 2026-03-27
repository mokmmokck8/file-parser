"""
Document → base64 image conversion utilities.

PDF pages and images are converted to JPEG base64 strings
so they can be passed directly to the Qwen2.5-VL vision model.
"""

import base64
import io
import os

from PIL import Image

# Scale factor when rasterising PDF pages (1.5 ≈ 108 DPI, good balance of
# quality vs. token cost for a 7 B vision model).
_PDF_SCALE = float(os.getenv("PDF_RENDER_SCALE", "1.5"))
# JPEG quality used when encoding pages / images for the vision model.
_JPEG_QUALITY = int(os.getenv("VLM_JPEG_QUALITY", "85"))
# Maximum dimension (width or height) for images sent to the VLM.
_IMAGE_MAX_SIZE = int(os.getenv("VLM_IMAGE_MAX_SIZE", "1200"))


def _thumbnail_image(image: Image.Image, max_size: int = _IMAGE_MAX_SIZE) -> Image.Image:
    """
    Proportionally downscale *image* so neither dimension exceeds *max_size*.
    If the image is already within the limit it is returned unchanged.
    Uses LANCZOS resampling for best quality.
    """
    if image.width <= max_size and image.height <= max_size:
        return image
    image = image.copy()
    image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    return image


def _image_to_b64(image: Image.Image) -> str:
    """Convert a PIL Image to a base64-encoded JPEG string."""
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=_JPEG_QUALITY)
    return base64.b64encode(buf.getvalue()).decode()


def document_to_images_b64(content: bytes, content_type: str) -> list[str]:
    """
    Convert an uploaded document to a list of base64 JPEG strings.

    - PDF  → one entry per page (rendered via PyMuPDF)
    - Image → single entry
    """
    if content_type == "application/pdf":
        return _pdf_to_images_b64(content)
    image = Image.open(io.BytesIO(content))
    image = _thumbnail_image(image)
    return [_image_to_b64(image)]


def _pdf_to_images_b64(content: bytes) -> list[str]:
    """Render every page of a PDF to a base64 JPEG string."""
    import fitz  # type: ignore[import-untyped]  # pymupdf

    doc = fitz.open(stream=content, filetype="pdf")
    mat = fitz.Matrix(_PDF_SCALE, _PDF_SCALE)
    pages: list[str] = []
    for page in doc:  # type: ignore[union-attr]
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)  # type: ignore[union-attr]
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)  # type: ignore[arg-type]
        pages.append(_image_to_b64(img))
    doc.close()
    return pages
