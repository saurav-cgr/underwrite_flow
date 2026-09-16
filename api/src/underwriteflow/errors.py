"""Sanitized API error responses."""

from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorBody(BaseModel):
    """Stable machine-readable API error body."""

    code: str
    message: str
    request_id: str
    retryable: bool
    details: dict[str, Any] | None = None


class ErrorEnvelope(BaseModel):
    """Envelope returned for all API failures."""

    error: ErrorBody


class ApiError(Exception):
    """Expected sanitized application failure."""

    # Capture safe response fields without retaining request data.
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details


# Choose the client-facing message for one framework HTTP error.
def http_error_message(status_code: int, detail: object) -> str:
    if status_code >= 500:
        # A server error may describe internals, so it stays generic.
        return "Request could not be completed"
    if isinstance(detail, str) and detail:
        # Every detail in this codebase is either a hand-written message or an
        # application-owned error, so a client can safely read it.
        return detail
    return "Request could not be completed"


# Build a sanitized response with the shared error schema.
def error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    payload = ErrorEnvelope(
        error=ErrorBody(
            code=code,
            message=message,
            request_id=request_id,
            retryable=retryable,
            details=details,
        )
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(exclude_none=True))
