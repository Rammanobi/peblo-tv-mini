import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    """Structured application error matching the universal error envelope."""

    def __init__(
        self,
        status_code: int,
        type_: str,
        message: str,
        details: list[dict] | None = None,
    ):
        self.status_code = status_code
        self.type = type_
        self.message = message
        self.details = details or []


def new_request_id() -> str:
    return "req_" + uuid.uuid4().hex[:16].upper()


def envelope(type_: str, message: str, details: list[dict] | None = None) -> dict:
    return {
        "error": {
            "type": type_,
            "message": message,
            "request_id": new_request_id(),
            "details": details or [],
        }
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        return JSONResponse(
            status_code=exc.status_code,
            content=envelope(exc.type, exc.message, exc.details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        type_map = {401: "unauthorized", 403: "forbidden", 404: "not_found", 400: "validation_error"}
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content=envelope(type_map.get(exc.status_code, "internal_error"), detail),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        details = []
        for err in exc.errors():
            field = ".".join(str(p) for p in err.get("loc", []) if p != "body")
            details.append(
                {
                    "code": "MALFORMED_REQUEST",
                    "field": field,
                    "message": err.get("msg", "Invalid value."),
                    "hint": None,
                    "resource": None,
                }
            )
        return JSONResponse(
            status_code=400,
            content=envelope("validation_error", "The request body could not be parsed.", details),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=envelope("internal_error", "An unexpected error occurred."),
        )
