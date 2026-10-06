from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routers import auth, documents


app = FastAPI(title="DocFlow API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code_by_status = {
        400: "validation_error",
        401: "unauthorized",
        403: "unauthorized",
        404: "not_found",
        409: "conflict",
        413: "file_too_large",
        415: "unsupported_type",
        422: "validation_error",
        500: "internal_error",
    }
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        code = exc.detail["code"]
        message = exc.detail.get("message", "")
    else:
        code = code_by_status.get(
            exc.status_code,
            "validation_error" if exc.status_code < 500 else "internal_error",
        )
        message = str(exc.detail) if exc.detail is not None else ""

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": message}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "Invalid request"}},
    )


@app.exception_handler(Exception)
async def internal_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "Internal server error"}},
    )


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health")
def root_health() -> dict[str, str]:
    return {"status": "ok"}
