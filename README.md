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
│   └── extract.py     # /extract/entity and /extract/individualProfile routes
├── services/
│   ├── image_converter.py  # Document → base64 image conversion (PDF via PyMuPDF)
│   └── llm.py              # Qwen2.5-VL via Ollama — structured extraction
├── test/
│   ├── entity_extraction/
│   │   ├── test_batch.py   # Batch test for /extract/entity
│   │   └── test_files/     # Place test files here (git-ignored except .gitkeep)
│   └── individual_profile_extraction/
│       ├── test_batch.py   # Batch test for /extract/individualProfile
│       └── test_files/     # Place test files here (git-ignored except .gitkeep)
├── .env               # Local environment variables (do not commit)
├── .env.example       # Environment variable template (commit this)
├── pyproject.toml     # Project metadata and dependencies
├── poetry.lock        # Locked dependency versions
└── README.md
```

## Available Endpoints

| Method | Path                         | Description                                      |
| ------ | ---------------------------- | ------------------------------------------------ |
| `GET`  | `/`                          | Health check                                     |
| `POST` | `/extract/entity`            | Upload a document to extract company/entity info |
| `POST` | `/extract/individualProfile` | Upload a document to extract individual profile  |

### `POST /extract/entity`

**Accepted file types:** `image/jpeg`, `image/png`, `image/gif`, `image/webp`, `application/pdf`

**Response:**

```json
{
  "companyName": "ACME LIMITED",
  "entityIdentifier": "12345678",
  "countryISOCode": "HKG",
  "companyType": "PRIVATE_COMPANY_LIMITED_BY_SHARES",
  "incorporationDate": "2020-01-15"
}
```

**Error codes:**

| Status | Meaning                                           |
| ------ | ------------------------------------------------- |
| `415`  | Unsupported file type                             |
| `500`  | Document conversion failed (e.g. corrupt PDF)     |
| `502`  | Ollama is unreachable or the VLM inference failed |

---

### `POST /extract/individualProfile`

**Accepted file types:** `image/jpeg`, `image/png`, `image/gif`, `image/webp`, `application/pdf`

**Response:**

```json
{
  "name": "JOHN DOE",
  "idType": "PASSPORT",
  "idNumber": "A12345678",
  "nationality": "HKG",
  "dateOfBirth": "1990-05-20",
  "idIssueDate": "2015-03-01",
  "idExpiryDate": "2025-03-01",
  "residentialAddress": "1 Example Street, Hong Kong",
  "correspondenceAddress": "1 Example Street, Hong Kong"
}
```

**Error codes:** same as `/extract/entity` above.

---

## Batch Testing

每個 endpoint 都有各自的批次測試腳本，位於 `test/` 資料夾下。腳本會一次上傳多個檔案到後端，並把每個檔案的測試結果輸出成 CSV 或 JSON。

### 前置準備

確保後端已啟動：

```bash
poetry run uvicorn main:app --reload
```

### 測試 `/extract/entity`

將要測試的圖片或 PDF 放入 `test/entity_extraction/test_files/`（此資料夾內容不會被 git 追蹤）：

```bash
cp /your/docs/*.jpg ./test/entity_extraction/test_files/
```

執行測試：

```bash
# 基本執行（循序、輸出 CSV）
poetry run python test/entity_extraction/test_batch.py

# 自訂資料夾與並行數
poetry run python test/entity_extraction/test_batch.py --workers 3 --format json

# 完整參數範例
poetry run python test/entity_extraction/test_batch.py \
  --dir ./test/entity_extraction/test_files \
  --url http://localhost:8000/extract/entity \
  --output ./results/entity_run1 \
  --format csv \
  --workers 2 \
  --timeout 120
```

### 測試 `/extract/individualProfile`

將要測試的圖片或 PDF 放入 `test/individual_profile_extraction/test_files/`：

```bash
cp /your/id_docs/*.jpg ./test/individual_profile_extraction/test_files/
```

執行測試：

```bash
# 基本執行（循序、輸出 CSV）
poetry run python test/individual_profile_extraction/test_batch.py

# 自訂資料夾與並行數
poetry run python test/individual_profile_extraction/test_batch.py --workers 3 --format json

# 完整參數範例
poetry run python test/individual_profile_extraction/test_batch.py \
  --dir ./test/individual_profile_extraction/test_files \
  --url http://localhost:8000/extract/individualProfile \
  --output ./results/profile_run1 \
  --format csv \
  --workers 2 \
  --timeout 120
```

### 參數說明（兩個腳本通用）

| 參數        | entity 預設值                          | individualProfile 預設值                          | 說明                       |
| ----------- | -------------------------------------- | ------------------------------------------------- | -------------------------- |
| `--dir`     | `./test_files`                         | `./test_files`                                    | 測試檔案資料夾             |
| `--url`     | `http://localhost:8000/extract/entity` | `http://localhost:8000/extract/individualProfile` | 後端 URL                   |
| `--output`  | `./test_results_<timestamp>`           | `./test_results_<timestamp>`                      | 輸出檔案路徑（不含副檔名） |
| `--format`  | `csv`                                  | `csv`                                             | 輸出格式：`csv` 或 `json`  |
| `--workers` | `1`                                    | `1`                                               | 並行請求數                 |
| `--timeout` | `300`                                  | `300`                                             | 每個請求的 timeout（秒）   |

支援的格式：`.jpg`、`.jpeg`、`.png`、`.gif`、`.webp`、`.pdf`

### 記錄欄位

**Entity extraction：**

| 欄位                | 說明                                    |
| ------------------- | --------------------------------------- |
| `filename`          | 檔案名稱                                |
| `file_size_kb`      | 檔案大小（KB）                          |
| `resolution`        | 圖片解析度（`WxH`）；PDF 顯示 `N/A`     |
| `response_time_s`   | 後端回應時間（秒）                      |
| `http_status`       | HTTP 狀態碼                             |
| `companyName`       | 公司名稱                                |
| `entityIdentifier`  | 公司識別碼                              |
| `countryISOCode`    | 國家 ISO 代碼                           |
| `companyType`       | 公司類型                                |
| `incorporationDate` | 成立日期                                |
| `error`             | 錯誤訊息（請求失敗或 timeout 時才有值） |

**Individual profile extraction：**

| 欄位                    | 說明                                    |
| ----------------------- | --------------------------------------- |
| `filename`              | 檔案名稱                                |
| `file_size_kb`          | 檔案大小（KB）                          |
| `resolution`            | 圖片解析度（`WxH`）；PDF 顯示 `N/A`     |
| `response_time_s`       | 後端回應時間（秒）                      |
| `http_status`           | HTTP 狀態碼                             |
| `name`                  | 姓名                                    |
| `idType`                | 證件類型                                |
| `idNumber`              | 證件號碼                                |
| `nationality`           | 國籍（ISO alpha-3）                     |
| `dateOfBirth`           | 出生日期                                |
| `idIssueDate`           | 證件簽發日期                            |
| `idExpiryDate`          | 證件到期日期                            |
| `residentialAddress`    | 住宅地址                                |
| `correspondenceAddress` | 通訊地址                                |
| `error`                 | 錯誤訊息（請求失敗或 timeout 時才有值） |

### 執行範例輸出

```
============================================================
🚀  File Parser — Individual Profile Batch Test
============================================================
  Target URL  : http://localhost:8000/extract/individualProfile
  Test folder : /Users/you/workspace/file-parser/test/individual_profile_extraction/test_files
  Files found : 2
  Workers     : 1
  Timeout     : 300.0s
  Output      : /Users/you/workspace/file-parser/test_results_20260323_120000.csv
============================================================

🔍 Testing: passport_sample.jpg
✅ passport_sample.jpg  |  210.45 KB  |  1800x1200  |  4.32 s  |  HTTP 200
           name=JOHN DOE  idType=PASSPORT  idNumber=A12345678  nationality=HKG  dob=1990-05-20
           issueDate=2015-03-01  expiryDate=2025-03-01
           residentialAddress=1 Example Street, Hong Kong
           correspondenceAddress=1 Example Street, Hong Kong

🔍 Testing: national_id.png
✅ national_id.png  |  98.20 KB  |  1024x768  |  3.87 s  |  HTTP 200
           name=JANE SMITH  idType=NATIONAL_ID  idNumber=B98765432  nationality=GBR  dob=1985-11-03
           issueDate=2018-06-15  expiryDate=2028-06-14
           residentialAddress=10 Downing Street, London
           correspondenceAddress=10 Downing Street, London

============================================================
📊  Test Summary
============================================================
  Total files     : 2
  ✅ Success       : 2
  ❌ Failed        : 0
  Avg response    : 4.10 s
  Min response    : 3.87 s
  Max response    : 4.32 s
  Total wall time : 8.19 s
============================================================

💾  Results saved to: /Users/you/workspace/file-parser/test_results_20260323_120000.csv
```
