# file-parser

A FastAPI-based file parser service. Upload an image or PDF and the API will use **Qwen2.5-VL** (via Ollama) to directly extract structured company information from the document — no separate OCR step needed.

## Prerequisites

- Python **3.13** (paddlepaddle does not yet support Python 3.14)
- [Poetry](https://python-poetry.org/docs/#installation)
- [Ollama](https://ollama.com) — must be running locally with `qwen2.5vl:7b` pulled

### Install system dependencies (macOS)

```bash
brew install python@3.13
```

### Install and start Ollama

1. Download and install Ollama from [https://ollama.com](https://ollama.com), or via Homebrew:

```bash
brew install ollama
```

2. Pull the Qwen2.5-VL 7B model:

```bash
ollama pull qwen2.5vl:7b
```

3. Start the Ollama server (runs on `http://localhost:11434` by default):

```bash
ollama serve
```

> **Note:** Ollama must be running before you start the API server. If it is not running, VLM inference calls will return a `502` error.

## Getting Started

### 1. Install Poetry (if not already installed)

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Clone the repository

```bash
git clone <your-repo-url>
cd file-parser
```

### 3. Install dependencies

```bash
poetry env use /opt/homebrew/bin/python3.13
poetry install
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` to configure your environment:

| Variable           | Default                  | Description                                                                                 |
| ------------------ | ------------------------ | ------------------------------------------------------------------------------------------- |
| `ENV`              | `development`            | Set to `production` to enable strict CORS origin checks                                     |
| `ALLOWED_ORIGINS`  | _(empty)_                | Comma-separated list of allowed origins (production only), e.g. `https://your-frontend.com` |
| `OLLAMA_BASE_URL`  | `http://localhost:11434` | Base URL of the Ollama server                                                               |
| `OLLAMA_MODEL`     | `qwen2.5vl:7b`           | Ollama model name (must be a vision-language model)                                         |
| `OLLAMA_TIMEOUT`   | `300`                    | Seconds to wait for an Ollama response before timing out                                    |
| `PDF_RENDER_SCALE` | `1.5`                    | PDF rasterisation scale factor (higher = better quality, more tokens)                       |
| `VLM_JPEG_QUALITY` | `85`                     | JPEG quality when encoding pages for the VLM (1–95)                                         |

### 5. Run the development server

```bash
poetry run uvicorn main:app --reload
```

The API will be available at: [http://localhost:8000](http://localhost:8000)

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Project Structure

```
file-parser/
├── main.py            # FastAPI application entry point
├── routers/
│   └── upload.py      # File upload route
├── services/
│   ├── ocr.py         # Document → base64 image conversion (PDF via PyMuPDF)
│   └── llm.py         # Qwen2.5-VL via Ollama — direct vision extraction
├── tests/
│   ├── test_batch.py  # Batch testing tool (see below)
│   └── test_files/    # Place test files here (git-ignored except .gitkeep)
├── .env               # Local environment variables (do not commit)
├── .env.example       # Environment variable template (commit this)
├── pyproject.toml     # Project metadata and dependencies
├── poetry.lock        # Locked dependency versions
└── README.md
```

## Available Endpoints

| Method | Path      | Description                                        |
| ------ | --------- | -------------------------------------------------- |
| `GET`  | `/`       | Health check                                       |
| `POST` | `/upload` | Upload an image or PDF to extract the company name |

### `POST /upload`

**Accepted file types:** `image/jpeg`, `image/png`, `image/gif`, `image/webp`, `application/pdf`

**Response:**

```json
{ "companyName": "某某有限公司" }
```

If the company name cannot be determined:

```json
{ "companyName": null }
```

**Error codes:**

| Status | Meaning                                           |
| ------ | ------------------------------------------------- |
| `415`  | Unsupported file type                             |
| `500`  | Document conversion failed (e.g. corrupt PDF)     |
| `502`  | Ollama is unreachable or the VLM inference failed |

---

## Batch Testing (`test_batch.py`)

`test_batch.py` 是一個批次測試工具，可以一次上傳多個檔案到後端，並記錄每個檔案的測試結果。

### 準備測試檔案

將要測試的圖片或 PDF 放入 `tests/test_files/` 資料夾（此資料夾內容不會被 git 追蹤）：

```bash
cp /your/images/*.jpg ./tests/test_files/
cp /your/docs/*.pdf   ./tests/test_files/
```

支援的格式：`.jpg`、`.jpeg`、`.png`、`.gif`、`.webp`、`.pdf`

### 執行方式

確保後端已啟動（`poetry run uvicorn main:app --reload`），再執行：

```bash
# 基本執行（循序、輸出 CSV）
poetry run python tests/test_batch.py

# 自訂資料夾
poetry run python tests/test_batch.py --dir ./tests/test_files

# 3 個並行請求、輸出 JSON
poetry run python tests/test_batch.py --workers 3 --format json

# 完整參數範例
poetry run python tests/test_batch.py \
  --dir ./tests/test_files \
  --url http://localhost:8000/upload \
  --output ./results/run1 \
  --format csv \
  --workers 2 \
  --timeout 120
```

### 參數說明

| 參數        | 預設值                         | 說明                       |
| ----------- | ------------------------------ | -------------------------- |
| `--dir`     | `./tests/test_files`           | 測試檔案資料夾             |
| `--url`     | `http://localhost:8000/upload` | 後端上傳 URL               |
| `--output`  | `./test_results_<timestamp>`   | 輸出檔案路徑（不含副檔名） |
| `--format`  | `csv`                          | 輸出格式：`csv` 或 `json`  |
| `--workers` | `1`                            | 並行請求數                 |
| `--timeout` | `60`                           | 每個請求的 timeout（秒）   |

### 記錄欄位

| 欄位               | 說明                                    |
| ------------------ | --------------------------------------- |
| `filename`         | 檔案名稱                                |
| `file_size_kb`     | 檔案大小（KB）                          |
| `resolution`       | 圖片解析度（`WxH`）；PDF 顯示 `N/A`     |
| `response_time_ms` | 後端回應時間（毫秒）                    |
| `http_status`      | HTTP 狀態碼                             |
| `companyName`      | 回應：公司名稱                          |
| `entityIdentifier` | 回應：公司識別碼                        |
| `countryISOCode`   | 回應：國家 ISO 代碼                     |
| `companyType`      | 回應：公司類型                          |
| `error`            | 錯誤訊息（請求失敗或 timeout 時才有值） |

### 執行範例輸出

```
============================================================
🚀  File Parser — Batch Test
============================================================
  Target URL  : http://localhost:8000/upload
  Test folder : /Users/you/workspace/file-parser/test_files
  Files found : 3
  Workers     : 1
  Timeout     : 60.0s
  Output      : /Users/you/workspace/file-parser/test_results_20260313_120000.csv
============================================================

[1/3] ✅ sample1.jpg  |  142.35 KB  |  1200x900  |  3201.4 ms  |  HTTP 200
         company=ABC Holdings Ltd  id=12345678  country=HK  type=Limited
[2/3] ✅ sample2.png  |  88.10 KB   |  800x600   |  2874.0 ms  |  HTTP 200
         company=XYZ Corp  id=null  country=US  type=Corporation
[3/3] ❌ broken.pdf   |  5.20 KB    |  N/A       |  None ms    |  HTTP None
         ⚠️  Error: Timeout after 60.0s

============================================================
📊  Test Summary
============================================================
  Total files     : 3
  ✅ Success       : 2
  ❌ Failed        : 1
  Avg response    : 3037.7 ms
  Min response    : 2874.0 ms
  Max response    : 3201.4 ms
  Total wall time : 9.08 s
============================================================

💾  Results saved to: /Users/you/workspace/file-parser/test_results_20260313_120000.csv
```
