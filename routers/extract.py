from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from services.llm import extract_document_info, extract_individual_profile
from services.image_converter import document_to_images_b64

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
}


class EntityResponse(BaseModel):
    companyName: str | None
    entityIdentifier: str | None
    countryISOCode: str | None
    companyType: str | None
    incorporationDate: str | None


class IndividualProfileResponse(BaseModel):
    name: str | None
    idType: str | None
    idNumber: str | None
    nationality: str | None
    dateOfBirth: str | None
    idIssueDate: str | None
    idExpiryDate: str | None
    residentialAddress: str | None
    correspondenceAddress: str | None


async def _convert_and_read(file: UploadFile) -> tuple[bytes, list[str]]:
    """Read the uploaded file and convert it to a list of base64 image strings."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"不支援的檔案類型：{file.content_type}。只接受 image（jpeg、jpg、png、gif、webp）和 PDF。",
        )

    contents = await file.read()

    try:
        images_b64 = document_to_images_b64(contents, file.content_type or "")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"文件轉換失敗：{exc}") from exc

    print(f"=== 文件轉換完成：{len(images_b64)} 頁 ===")
    return contents, images_b64


@router.post("/extract/entity", response_model=EntityResponse)
async def extract_entity(file: UploadFile = File(...)) -> EntityResponse:
    _, images_b64 = await _convert_and_read(file)

    if not images_b64:
        return EntityResponse(companyName=None, entityIdentifier=None, countryISOCode=None, companyType=None, incorporationDate=None)

    # Send images to Qwen2.5-VL for structured extraction
    try:
        doc_info = await extract_document_info(images_b64, filename=file.filename or "")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"VLM 推論失敗：{exc}") from exc

    print("=== VLM 結果 ===")
    print(f"companyName:      {doc_info.company_name}")
    print(f"entityIdentifier: {doc_info.entity_identifier}")
    print(f"countryISOCode:   {doc_info.country_iso_code}")
    print(f"companyType:      {doc_info.company_type}")
    print(f"incorporationDate:{doc_info.incorporation_date}")
    print("================")

    return EntityResponse(
        companyName=doc_info.company_name,
        entityIdentifier=doc_info.entity_identifier,
        countryISOCode=doc_info.country_iso_code,
        companyType=doc_info.company_type,
        incorporationDate=doc_info.incorporation_date,
    )


@router.post("/extract/individualProfile", response_model=IndividualProfileResponse)
async def extract_individual(file: UploadFile = File(...)) -> IndividualProfileResponse:
    _, images_b64 = await _convert_and_read(file)

    if not images_b64:
        return IndividualProfileResponse(
            name=None, idType=None, idNumber=None, nationality=None,
            dateOfBirth=None, idIssueDate=None, idExpiryDate=None,
            residentialAddress=None, correspondenceAddress=None,
        )

    # Send images to Qwen2.5-VL for structured extraction
    try:
        profile = await extract_individual_profile(images_b64, filename=file.filename or "")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"VLM 推論失敗：{exc}") from exc

    print("=== VLM 結果 ===")
    print(f"name:                  {profile.name}")
    print(f"idType:                {profile.id_type}")
    print(f"idNumber:              {profile.id_number}")
    print(f"nationality:           {profile.nationality}")
    print(f"dateOfBirth:           {profile.date_of_birth}")
    print(f"idIssueDate:           {profile.id_issue_date}")
    print(f"idExpiryDate:          {profile.id_expiry_date}")
    print(f"residentialAddress:    {profile.residential_address}")
    print(f"correspondenceAddress: {profile.correspondence_address}")
    print("================")

    return IndividualProfileResponse(
        name=profile.name,
        idType=profile.id_type,
        idNumber=profile.id_number,
        nationality=profile.nationality,
        dateOfBirth=profile.date_of_birth,
        idIssueDate=profile.id_issue_date,
        idExpiryDate=profile.id_expiry_date,
        residentialAddress=profile.residential_address,
        correspondenceAddress=profile.correspondence_address,
    )
