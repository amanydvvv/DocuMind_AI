"""
DocuMind AI — Rate Limiting
Shared slowapi limiter instance keyed by real client IP (X-Forwarded-For).
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _rate_limit_key(request: Request) -> str:
    """
    Key rate limits by real client IP behind Render's reverse proxy.

    Render appends the true connecting client IP to the end of the
    X-Forwarded-For header chain:
        X-Forwarded-For: <spoofed_ip>, <actual_connecting_ip>

    Taking split(',')[0] allows clients to bypass rate limits by spoofing.
    Taking split(',')[-1] extracts the untamperable IP appended by Render.
    Falls back to request.client.host if X-Forwarded-For is missing.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


limiter = Limiter(key_func=_rate_limit_key, default_limits=[])
