from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from services.llm import extract_document_info
from services.ocr import document_to_images_b64

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

    # Step 1: Convert document to base64 images (one per page for PDF)
    try:
        images_b64 = document_to_images_b64(contents, file.content_type or "")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"文件轉換失敗：{exc}") from exc

    print(f"=== 文件轉換完成：{len(images_b64)} 頁 ===")

    if not images_b64:
        return ParseResponse(companyName=None, entityIdentifier=None, countryISOCode=None, companyType=None)

    # Step 2: Send images directly to Qwen2.5-VL for structured extraction
    try:
        doc_info = await extract_document_info(images_b64, filename=file.filename or "")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"VLM 推論失敗：{exc}") from exc

    print("=== VLM 結果 ===")
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
