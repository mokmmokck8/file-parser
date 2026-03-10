import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import upload

load_dotenv()

IS_DEV = os.getenv("ENV", "development") == "development"

if IS_DEV:
    allow_origins = ["*"]
else:
    raw = os.getenv("ALLOWED_ORIGINS", "")
    allow_origins = [o.strip() for o in raw.split(",") if o.strip()]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)


@app.get("/")
def read_root():
    return {"Hello": "World"}
