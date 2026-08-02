"""
DocuMind AI — Rate Limiting
Shared slowapi limiter instance keyed by real client IP (X-Forwarded-For).
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _rate_limit_key(request: Request) -> str:
    """Key rate limits by real client IP when behind Render's proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key, default_limits=[])
