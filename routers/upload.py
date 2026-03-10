from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from services.llm import extract_company_name
from services.ocr import extract_text_from_image_bytes

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
}


class ParseResponse(BaseModel):
    companyName: str | None


@router.post("/upload", response_model=ParseResponse)
async def upload_file(file: UploadFile = File(...)) -> ParseResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"不支援的檔案類型：{file.content_type}。只接受 image（jpeg、jpg、png、gif、webp）和 PDF。",
        )

    contents = await file.read()

    # Step 1: OCR — extract all text from the document
    try:
        ocr_text = extract_text_from_image_bytes(contents, file.content_type or "")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OCR 處理失敗：{exc}") from exc

    print("=== OCR 結果 ===")
    print(ocr_text)
    print("================")

    if not ocr_text.strip():
        return ParseResponse(companyName=None)

    # Step 2: LLM — ask Qwen2.5:7b to identify the company name
    try:
        company_name = await extract_company_name(ocr_text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM 推論失敗：{exc}") from exc

    print("=== LLM 結果 ===")
    print(company_name)
    print("================")

    return ParseResponse(companyName=company_name)
