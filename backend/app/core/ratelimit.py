"""
DocuMind AI — Rate Limiting
Shared slowapi limiter instance keyed by the real client IP.

Rate Limiting Key Resolution Priority:
1. CF-Connecting-IP: Injected by Cloudflare at the outer edge when traffic
   routes through Cloudflare to a custom domain. Overwritten at the edge so
   clients CANNOT spoof it.
2. request.client.host: Socket connection peer IP fallback when CF-Connecting-IP
   is absent (e.g. direct-origin requests to *.onrender.com or local integration tests).
   X-Forwarded-For is explicitly IGNORED when CF-Connecting-IP is absent to prevent
   client-supplied header spoofing attacks on direct-origin routes.
"""

import logging

logger = logging.getLogger(__name__)

from fastapi import Request
from slowapi import Limiter


def _rate_limit_key(request: Request) -> str:
    """
    Key rate limits by real client IP.

    1. CF-Connecting-IP: Untamperable edge IP set by Cloudflare when traffic
       routes through Cloudflare to a custom domain.
    2. request.client.host: Socket connection IP fallback when CF-Connecting-IP
       is absent (e.g. direct-origin requests to *.onrender.com or local tests).
       X-Forwarded-For is explicitly IGNORED when CF-Connecting-IP is absent to prevent
       client-supplied header spoofing attacks on direct-origin routes.
    """
    cf_ip = request.headers.get("cf-connecting-ip") or "ABSENT"
    forwarded = request.headers.get("x-forwarded-for") or "ABSENT"
    peer = request.client.host if request.client else "ABSENT"
    log_line = f"RATELIMIT_DEBUG cf={cf_ip} xff={forwarded} peer={peer}"
    logger.info(log_line)
    print(log_line, flush=True)

    if cf_ip != "ABSENT":
        return cf_ip.strip()

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


limiter = Limiter(key_func=_rate_limit_key, default_limits=[])
