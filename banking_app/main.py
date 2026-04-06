from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from database import init_db
from routes.account import router as account_router
from routes.auth import router as auth_router
from routes.loan import router as loan_router
from routes.transaction import router as transaction_router
from utils.rate_limit import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Banking App API", version="1.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://127.0.0.1:3000,http://localhost:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again later."})


@app.get("/")
async def root() -> dict:
    return {"message": "Banking App API is running"}


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(account_router)
app.include_router(transaction_router)
app.include_router(loan_router)
