import io
import os
import tempfile
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


def _results_to_text(results: list[Any]) -> str:
    """從 predict() 回傳的 OCRResult list 提取文字。"""
    all_text: list[str] = []
    for result in results or []:
        rec_texts: list[str] = result.get("rec_texts", [])
        page_text = "\n".join(rec_texts)
        if page_text.strip():
            all_text.append(page_text)
    return "\n\n".join(all_text)


def _image_to_text(image: Image.Image) -> str:
    ocr: Any = _get_ocr()
    img_array: NDArray[np.uint8] = np.array(image.convert("RGB"), dtype=np.uint8)
    results: list[Any] = ocr.predict(img_array)
    return _results_to_text(results)


def extract_text_from_image_bytes(content: bytes, content_type: str) -> str:
    """Extract all text from an uploaded image or PDF using PaddleOCR."""
    if content_type == "application/pdf":
        return _extract_text_from_pdf(content)
    image = Image.open(io.BytesIO(content))
    return _image_to_text(image)


def _extract_text_from_pdf(content: bytes) -> str:
    """直接讓 PaddleOCR predict() 處理 PDF，不需手動轉圖片。"""
    ocr: Any = _get_ocr()
    # predict() 需要檔案路徑，將 bytes 寫入暫存檔後傳入
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        results: list[Any] = ocr.predict(tmp_path)
        return _results_to_text(results)
    finally:
        os.remove(tmp_path)
