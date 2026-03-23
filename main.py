import asyncio
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import RequestResponseEndpoint
from dotenv import load_dotenv
from routers import extract

load_dotenv()

IS_DEV = os.getenv("ENV", "development") == "development"

if IS_DEV:
    allow_origins = ["*"]
else:
    raw = os.getenv("ALLOWED_ORIGINS", "")
    allow_origins = [o.strip() for o in raw.split(",") if o.strip()]

# Allow at most 2 concurrent requests
_concurrency_semaphore = asyncio.Semaphore(2)

app = FastAPI()


@app.middleware("http")
async def limit_concurrency(request: Request, call_next: RequestResponseEndpoint) -> Response:
    if _concurrency_semaphore._value == 0:  # noqa: SLF001
        return JSONResponse(
            status_code=503,
            content={"detail": "伺服器繁忙，目前已有 2 個請求在處理中，請稍後再試。"},
        )
    async with _concurrency_semaphore:
        return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extract.router)


@app.get("/")
def read_root():
    return {"Hello": "World"}
