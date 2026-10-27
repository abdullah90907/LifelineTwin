"""Allowlisted failure metadata. Never serialize exception messages, prompts or bodies."""
import math
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CODES = {
    "rate_limit_exceeded", "rate_limit_error", "requests_limit_exceeded", "tokens_limit_exceeded",
    "tool_use_failed", "invalid_request_error", "context_length_exceeded", "invalid_api_key",
    "authentication_error", "insufficient_quota", "billing_hard_limit_reached", "model_not_found",
    "permission_denied", "server_error", "internal_server_error", "service_unavailable",
    "overloaded_error", "capacity_exceeded", "timeout",
}


class FailureMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    category: Literal["rate_limit", "service_failure", "timeout", "transport", "authentication",
                      "provider_request", "malformed_tool_call", "invalid_agent_output",
                      "invalid_tool_arguments", "worker_failure", "execution_limit", "analytical_tool", "context_budget", "rate_budget"]
    http_status: int | None = Field(default=None, ge=100, le=599)
    provider_code: str | None = None
    request_id: str | None = None
    transient: bool = False
    retry_after_seconds: float | None = Field(default=None, ge=0, le=86400, allow_inf_nan=False)
    retry_after_supplied: bool = False
    stage: str = "provider_sdk"


class ProviderFailure(RuntimeError):
    def __init__(self, metadata):
        self.metadata = metadata if isinstance(metadata, FailureMetadata) else FailureMetadata.model_validate(metadata)
        super().__init__("Classified failure: " + self.metadata.category)


def safe_request_id(value):
    if not isinstance(value, str) or len(value) > 110 or "gsk_" in value or "sk-" in value:
        return None
    if re.fullmatch(r"req[_-][A-Za-z0-9_-]{1,100}", value) or re.fullmatch(r"[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}", value):
        return value
    return None


def parse_retry_after(value, wall_now=None):
    if not isinstance(value, str) or len(value) > 100:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            seconds = max(0.0, (date - (wall_now or datetime.now(timezone.utc))).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return None
    return seconds if math.isfinite(seconds) and 0 <= seconds <= 86400 else None


def classify_exception(exc):
    if isinstance(exc, ProviderFailure):
        # Revalidate the process boundary and remove unconstrained identifier values.
        data = exc.metadata.model_dump()
        data["provider_code"] = data["provider_code"] if data["provider_code"] in CODES else None
        data["request_id"] = safe_request_id(data["request_id"])
        data["stage"] = data["stage"] if data["stage"] in ("provider_sdk", "provider_response", "provider_worker", "context_management", "provider_budget") else "provider_sdk"
        return FailureMetadata(**data)
    import httpx
    from openai import APIStatusError, APITimeoutError, APIConnectionError
    if isinstance(exc, (APITimeoutError, httpx.TimeoutException)):
        return FailureMetadata(category="timeout")
    if isinstance(exc, (APIConnectionError, httpx.TransportError)):
        return FailureMetadata(category="transport")
    if isinstance(exc, APIStatusError):
        status = exc.status_code
        body = exc.body if isinstance(exc.body, dict) else {}
        detail = body.get("error", body)
        code = detail.get("code") if isinstance(detail, dict) else None
        code = code if isinstance(code, str) and code in CODES else ("invalid_request_error" if status == 400 else None)
        headers = exc.response.headers
        retry = headers.get("retry-after")
        request_id = safe_request_id(getattr(exc, "request_id", None)) or safe_request_id(headers.get("x-request-id"))
        if code == "tool_use_failed":
            category, transient = "malformed_tool_call", False
        elif status == 429:
            category = "rate_limit"
            transient = code in {"rate_limit_exceeded", "rate_limit_error", "requests_limit_exceeded", "tokens_limit_exceeded"}
        elif status in (500, 502, 503, 504):
            category, transient = "service_failure", True
        elif status in (401, 403):
            category, transient = "authentication", False
        else:
            category, transient = "provider_request", False
        return FailureMetadata(category=category, http_status=status, provider_code=code, request_id=request_id,
            transient=transient, retry_after_supplied=retry is not None, retry_after_seconds=parse_retry_after(retry))
    return FailureMetadata(category="worker_failure", stage="provider_worker")
