import io
import os
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PIL import Image

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

_ocr_instance: Any = None


def _get_ocr() -> Any:
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR  # type: ignore[import-untyped]

        _ocr_instance = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang="ch",  # supports Chinese + English
        )
    return _ocr_instance


def _image_to_text(image: Image.Image) -> str:
    ocr: Any = _get_ocr()
    img_array: NDArray[np.uint8] = np.array(image.convert("RGB"), dtype=np.uint8)
    results: list[Any] = ocr.predict(img_array)
    lines: list[str] = []
    for result in results:
        rec_texts: list[str] = result.get("rec_texts", [])
        lines.extend(rec_texts)
    return "\n".join(lines)


def extract_text_from_image_bytes(content: bytes, content_type: str) -> str:
    """Extract all text from an uploaded image or PDF using PaddleOCR."""
    if content_type == "application/pdf":
        return _extract_text_from_pdf(content)
    image = Image.open(io.BytesIO(content))
    return _image_to_text(image)


def _extract_text_from_pdf(content: bytes) -> str:
    from pdf2image import convert_from_bytes  # type: ignore[import-untyped]

    images: list[Image.Image] = convert_from_bytes(content, dpi=200)
    all_text: list[str] = []
    for img in images:
        page_text = _image_to_text(img)
        if page_text.strip():
            all_text.append(page_text)
    return "\n\n".join(all_text)
