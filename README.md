# file-parser

A FastAPI-based file parser service. Upload an image or PDF and the API will use **PaddleOCR** to extract text, then feed it to **Qwen2.5:7b** (via Ollama) to identify the company name.

## Prerequisites

- Python **3.13** (paddlepaddle does not yet support Python 3.14)
- [Poetry](https://python-poetry.org/docs/#installation)
- [Ollama](https://ollama.com) — must be running locally with `qwen2.5:7b` pulled
- [poppler](https://poppler.freedesktop.org/) — required by `pdf2image` for PDF support

### Install system dependencies (macOS)

```bash
brew install python@3.13 poppler
```

### Install and start Ollama

1. Download and install Ollama from [https://ollama.com](https://ollama.com), or via Homebrew:

```bash
brew install ollama
```

2. Pull the Qwen2.5 7B model:

```bash
ollama pull qwen2.5:7b
```

3. Start the Ollama server (runs on `http://localhost:11434` by default):

```bash
ollama serve
```

> **Note:** Ollama must be running before you start the API server. If it is not running, LLM inference calls will return a `502` error.

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

| Variable          | Default                  | Description                                                                                 |
| ----------------- | ------------------------ | ------------------------------------------------------------------------------------------- |
| `ENV`             | `development`            | Set to `production` to enable strict CORS origin checks                                     |
| `ALLOWED_ORIGINS` | _(empty)_                | Comma-separated list of allowed origins (production only), e.g. `https://your-frontend.com` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Base URL of the Ollama server                                                               |
| `OLLAMA_MODEL`    | `qwen2.5:7b`             | Ollama model name to use for company name extraction                                        |
| `OLLAMA_TIMEOUT`  | `120`                    | Seconds to wait for an Ollama response before timing out                                    |

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
│   ├── ocr.py         # PaddleOCR text extraction (images & PDFs)
│   └── llm.py         # Qwen2.5:7b via Ollama — company name extraction
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
| `500`  | OCR processing failed                             |
| `502`  | Ollama is unreachable or the LLM inference failed |
