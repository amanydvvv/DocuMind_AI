"""
DocuMind AI — Rate Limiting
Shared slowapi limiter instance keyed by the real client IP.

Peer-anchored CF-Connecting-IP resolution:
The CF-Connecting-IP header (set by Cloudflare at the outer edge) is only
trusted when the immediate TCP peer (request.client.host) is a private address,
which is what Render's internal proxy presents. Direct-origin requests (e.g.
*.onrender.com) and local integration tests reach the app with a public or
loopback peer, so the header is ignored and the peer IP is used instead.
X-Forwarded-For is never consulted: clients can trivially spoof it.
"""

from fastapi import Request
from slowapi import Limiter

_PRIVATE_IP_PREFIXES = ("10.", "172.16.", "192.168.", "127.", "::1", "fc00:", "fe80:")


def _rate_limit_key(request: Request) -> str:
    """
    Key rate limits by real client IP.

    1. CF-Connecting-IP: Trusted ONLY when the TCP peer (request.client.host)
       starts with a private IP prefix, i.e. traffic proxied by Render's
       internal proxy where the header is set at the edge and cannot be spoofed.
    2. request.client.host: Socket connection peer otherwise. Never spoofable
       because it comes from the TCP connection itself.
    """
    peer = request.client.host if request.client and request.client.host else "127.0.0.1"

    if peer.startswith(_PRIVATE_IP_PREFIXES):
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()

    return peer


limiter = Limiter(key_func=_rate_limit_key, default_limits=[])
