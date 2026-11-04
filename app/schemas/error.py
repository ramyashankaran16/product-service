"""The single error format used by every endpoint (used for OpenAPI docs)."""
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: str
    issue: str


class ErrorResponse(BaseModel):
    timestamp: str
    status: int
    error: str
    message: str
    path: str
    details: list[ErrorDetail] = []
