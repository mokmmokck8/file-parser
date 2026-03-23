import json
import os
from typing import Any

import httpx

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5vl:7b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "300"))
# Maximum number of pages to send to the VLM. Company info is almost always
# on the first 1-2 pages; sending too many pages confuses 7B models.
VLM_MAX_PAGES = int(os.getenv("VLM_MAX_PAGES", "1"))

_REQUIRED_KEYS = {"companyName", "entityIdentifier", "countryISOCode", "companyType", "incorporationDate"}

_ENTITY_PROMPT_TEMPLATE = """You are a document information extraction assistant. Analyze the image of document %s and extract exactly these 5 fields:

1. companyName: The official registered company name (full legal name including Ltd/LLC/etc.). null if not found.
2. entityIdentifier: The company registration/tax/business ID number ONLY (digits and hyphens, no labels). null if not found.
3. countryISOCode: ISO 3166-1 alpha-3 country code (exactly 3 uppercase letters, e.g. HKG, USA, GBR, CHN). Infer from the document's jurisdiction or address. null if not found.
4. companyType: One of: PRIVATE_COMPANY_LIMITED_BY_SHARES, PUBLIC_COMPANY_LIMITED_BY_SHARES, PUBLIC_COMPANY_LIMITED_BY_GUARANTEE, LIMITED_LIABILITY_COMPANY, LIMITED_PARTNERSHIP, EXEMPTED_LIMITED_PARTNERSHIP, SEGREGATED_PORTFOLIO_COMPANY, EXEMPTED_COMPANY, EXEMPTED_LIMITED_COMPANY, UNLIMITED_COMPANY, GENERAL_PARTNERSHIP, SOLE_PROPRIETORSHIP, OTHERS. null if not found.
5. incorporationDate: The date the company was incorporated or registered, in ISO 8601 format (YYYY-MM-DD). null if not found.

Respond with ONLY a JSON object containing exactly these 5 keys. No explanation, no markdown, no extra keys.
Example: {"companyName":"ACME LIMITED","entityIdentifier":"12345678","countryISOCode":"HKG","companyType":"PRIVATE_COMPANY_LIMITED_BY_SHARES","incorporationDate":"2020-01-15"}"""


class DocumentInfo:
    def __init__(
        self,
        company_name: str | None,
        entity_identifier: str | None,
        country_iso_code: str | None,
        company_type: str | None,
        incorporation_date: str | None,
    ) -> None:
        self.company_name = company_name
        self.entity_identifier = entity_identifier
        self.country_iso_code = country_iso_code
        self.company_type = company_type
        self.incorporation_date = incorporation_date


async def extract_document_info(images_b64: list[str], filename: str = "") -> DocumentInfo:
    """
    Send document page images to Qwen2.5-VL via Ollama and extract structured info.

    Each element of images_b64 is a base64-encoded JPEG string representing one page.
    All pages are sent in a single multi-image message so the model has full context.
    """
    doc_label = f'"{filename}"' if filename else "(uploaded document)"
    prompt = _ENTITY_PROMPT_TEMPLATE % doc_label

    # Limit pages sent to the model — company info is almost always on the
    # first few pages, and too many images confuse smaller VLMs.
    pages = images_b64[:VLM_MAX_PAGES]

    message: dict[str, Any] = {
        "role": "user",
        "content": prompt,
        "images": pages,
    }
    payload: dict[str, Any] = {
        "model": OLLAMA_MODEL,
        "messages": [message],
        "stream": False,
        "format": "json",
    }

    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
        )
        response.raise_for_status()

    data: dict[str, Any] = response.json()
    raw_content: str = data["message"]["content"]

    try:
        parsed: dict[str, Any] = json.loads(raw_content)
        # Strip any extra keys the model may have added
        return DocumentInfo(
            company_name=parsed.get("companyName") or None,
            entity_identifier=parsed.get("entityIdentifier") or None,
            country_iso_code=parsed.get("countryISOCode") or None,
            company_type=parsed.get("companyType") or None,
            incorporation_date=parsed.get("incorporationDate") or None,
        )
    except (json.JSONDecodeError, KeyError):
        return DocumentInfo(None, None, None, None, None)


_INDIVIDUAL_PROMPT_TEMPLATE = """You are a document information extraction assistant. Analyze the image of document %s and extract exactly these 9 fields:

1. name: The individual's full legal name. null if not found.
2. idType: The type of identification document (e.g. PASSPORT, NATIONAL_ID, DRIVERS_LICENSE, OTHERS). null if not found.
3. idNumber: The identification document number ONLY (no labels). null if not found.
4. nationality: ISO 3166-1 alpha-3 country code of the individual's nationality (exactly 3 uppercase letters, e.g. HKG, USA, GBR). null if not found.
5. dateOfBirth: Date of birth in ISO 8601 format (YYYY-MM-DD). null if not found.
6. idIssueDate: Date the ID was issued in ISO 8601 format (YYYY-MM-DD). null if not found.
7. idExpiryDate: Date the ID expires in ISO 8601 format (YYYY-MM-DD). null if not found.
8. residentialAddress: The individual's full residential address as a single string. null if not found.
9. correspondenceAddress: The individual's correspondence/mailing address as a single string. If same as residential, repeat it. null if not found.

Respond with ONLY a JSON object containing exactly these 9 keys. No explanation, no markdown, no extra keys.
Example: {"name":"JOHN DOE","idType":"PASSPORT","idNumber":"A12345678","nationality":"HKG","dateOfBirth":"1990-05-20","idIssueDate":"2015-03-01","idExpiryDate":"2025-03-01","residentialAddress":"1 Example Street, Hong Kong","correspondenceAddress":"1 Example Street, Hong Kong"}"""


class IndividualInfo:
    def __init__(
        self,
        name: str | None,
        id_type: str | None,
        id_number: str | None,
        nationality: str | None,
        date_of_birth: str | None,
        id_issue_date: str | None,
        id_expiry_date: str | None,
        residential_address: str | None,
        correspondence_address: str | None,
    ) -> None:
        self.name = name
        self.id_type = id_type
        self.id_number = id_number
        self.nationality = nationality
        self.date_of_birth = date_of_birth
        self.id_issue_date = id_issue_date
        self.id_expiry_date = id_expiry_date
        self.residential_address = residential_address
        self.correspondence_address = correspondence_address


async def extract_individual_profile(images_b64: list[str], filename: str = "") -> IndividualInfo:
    """
    Send document page images to Qwen2.5-VL via Ollama and extract individual profile info.

    Each element of images_b64 is a base64-encoded JPEG string representing one page.
    All pages are sent in a single multi-image message so the model has full context.
    """
    doc_label = f'"{filename}"' if filename else "(uploaded document)"
    prompt = _INDIVIDUAL_PROMPT_TEMPLATE % doc_label

    pages = images_b64[:VLM_MAX_PAGES]

    message: dict[str, Any] = {
        "role": "user",
        "content": prompt,
        "images": pages,
    }
    payload: dict[str, Any] = {
        "model": OLLAMA_MODEL,
        "messages": [message],
        "stream": False,
        "format": "json",
    }

    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
        )
        response.raise_for_status()

    data: dict[str, Any] = response.json()
    raw_content: str = data["message"]["content"]

    try:
        parsed: dict[str, Any] = json.loads(raw_content)
        return IndividualInfo(
            name=parsed.get("name") or None,
            id_type=parsed.get("idType") or None,
            id_number=parsed.get("idNumber") or None,
            nationality=parsed.get("nationality") or None,
            date_of_birth=parsed.get("dateOfBirth") or None,
            id_issue_date=parsed.get("idIssueDate") or None,
            id_expiry_date=parsed.get("idExpiryDate") or None,
            residential_address=parsed.get("residentialAddress") or None,
            correspondence_address=parsed.get("correspondenceAddress") or None,
        )
    except (json.JSONDecodeError, KeyError):
        return IndividualInfo(None, None, None, None, None, None, None, None, None)
