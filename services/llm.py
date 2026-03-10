import json
import os
from typing import Any

import httpx

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))

_SYSTEM_PROMPT = """你是一個專業的文件分析助手。
你的任務是從 OCR 提取的文字中找出這份文件屬於哪間公司。
公司名稱可能是中文、英文或兩者皆有。
只需回傳一個 JSON 物件，格式如下：
{"companyName": "<公司名稱>"}
如果無法判斷，請回傳：
{"companyName": null}
不要輸出任何其他文字。"""


async def extract_company_name(ocr_text: str) -> str | None:
    """Send OCR text to Qwen2.5:7b via Ollama and extract the company name."""
    prompt = f"以下是從文件中 OCR 提取的文字：\n\n{ocr_text}\n\n請找出這份文件屬於哪間公司。"

    messages: list[dict[str, str]] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    payload: dict[str, Any] = {
        "model": OLLAMA_MODEL,
        "messages": messages,
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
        company: str | None = parsed.get("companyName") or None
        return company
    except (json.JSONDecodeError, KeyError):
        return None
