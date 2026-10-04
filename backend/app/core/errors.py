from typing import Optional, Dict, Any
from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class AppException(Exception):
    def __init__(self, code: str = "ERROR", message: str = "", status_code: int = 400, details: Optional[Dict[str, Any]] = None, error_code: Optional[str] = None):
        c = error_code or code
        super().__init__(message)
        self.code = c
        self.error_code = c
        self.message = message
        self.status_code = status_code
        self.details = details or {}

LucenError = AppException

def format_error_response(code: str, message: str, details: Optional[Dict[str, Any]] = None, status_code: int = 400) -> JSONResponse:
    content = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        }
    }
    return JSONResponse(status_code=status_code, content=content)

from fastapi.exceptions import RequestValidationError

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_msg = errors[0].get("msg", "Validation error") if errors else "Validation error"
    clean_errors = []
    for err in errors:
        c_err = dict(err)
        if "input" in c_err and not isinstance(c_err["input"], (str, int, float, bool, list, dict, type(None))):
            c_err["input"] = str(c_err["input"])
        clean_errors.append(c_err)
    return format_error_response(
        code="VALIDATION_ERROR",
        message=f"Request validation failed: {first_msg}",
        details={"errors": clean_errors},
        status_code=422
    )

async def app_exception_handler(request: Request, exc: AppException):
    return format_error_response(exc.code, exc.message, exc.details, exc.status_code)

async def http_exception_handler(request: Request, exc: HTTPException):
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        413: "FILE_TOO_LARGE",
        415: "UNSUPPORTED_FILE_TYPE",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
    }
    code = code_map.get(exc.status_code, "ERROR")
    # If detail is already formatted or dict
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", code)
        message = exc.detail.get("message", str(exc.detail))
        details = exc.detail.get("details", {})
    else:
        message = str(exc.detail) if exc.detail else "An error occurred"
        details = {}
        
    return format_error_response(code, message, details, exc.status_code)

async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return format_error_response(
        "INTERNAL_ERROR",
        "An unexpected error occurred",
        {"path": request.url.path, "error": str(exc)},
        status.HTTP_500_INTERNAL_SERVER_ERROR
    )
