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

_PROMPT_TEMPLATE = """You are a document information extraction assistant. Analyze the image of document %s and extract exactly these 5 fields:

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
    prompt = _PROMPT_TEMPLATE % doc_label

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
