# file-parser

A FastAPI-based file parser service.

## Prerequisites

- Python 3.14+
- [Poetry](https://python-poetry.org/docs/#installation)

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
poetry install
```

### 4. Run the development server

```bash
poetry run uvicorn main:app --reload
```

The API will be available at: [http://localhost:8000](http://localhost:8000)

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Project Structure

```
file-parser/
├── main.py          # FastAPI application entry point
├── pyproject.toml   # Project metadata and dependencies
├── poetry.lock      # Locked dependency versions
└── README.md
```

## Available Endpoints

| Method | Path | Description                |
| ------ | ---- | -------------------------- |
| GET    | `/`  | Health check / Hello World |
