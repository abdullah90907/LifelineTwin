"""Lightweight spawn-importable SDK exception fixture. Never makes HTTP requests."""


def raise_rate_limit():
    import httpx
    from openai import RateLimitError
    response = httpx.Response(429, headers={"x-request-id": "req_offline_123", "retry-after": "2"},
                              request=httpx.Request("POST", "https://provider.invalid/v1"))
    raise RateLimitError("SENSITIVE PROMPT MUST NOT BE STORED", response=response,
                        body={"error": {"code": "rate_limit_exceeded", "message": "SENSITIVE BODY"}})
