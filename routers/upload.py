from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from services.llm import extract_document_info
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
    entityIdentifier: str | None
    countryISOCode: str | None
    companyType: str | None


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
        return ParseResponse(companyName=None, entityIdentifier=None, countryISOCode=None, companyType=None)

    # Step 2: LLM — ask Qwen2.5:7b to extract structured document info
    try:
        doc_info = await extract_document_info(ocr_text, filename=file.filename or "")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM 推論失敗：{exc}") from exc

    print("=== LLM 結果 ===")
    print(f"companyName:      {doc_info.company_name}")
    print(f"entityIdentifier: {doc_info.entity_identifier}")
    print(f"countryISOCode:   {doc_info.country_iso_code}")
    print(f"companyType:      {doc_info.company_type}")
    print("================")

    return ParseResponse(
        companyName=doc_info.company_name,
        entityIdentifier=doc_info.entity_identifier,
        countryISOCode=doc_info.country_iso_code,
        companyType=doc_info.company_type,
    )
