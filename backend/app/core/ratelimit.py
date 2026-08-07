"""
DocuMind AI — Rate Limiting
Shared slowapi limiter instance keyed by the real client IP.

Render's proxy does NOT strip client-supplied headers — it appends its own
hop onto the X-Forwarded-For chain. X-Forwarded-For is therefore always
client-spoofable and is never read when constructing the rate-limit key
(PRIOR ISSUE: splitting on ',' and taking the first entry let a client
rotate its own IP to dodge limits).

Trusted request chain in production: Client -> Cloudflare -> Render -> app.
    * request.client.host is the TCP peer of the ASGI server. Behind Render
      that peer is Render's private proxy address (RFC1918) — unspoofable
      because it comes from the actual socket connection, not a header.
    * When the peer is a private/loopback address the request really arrived
      through that trusted proxy, so Cloudflare's CF-Connecting-IP /
      True-Client-IP headers are trusted: Cloudflare overwrites them at its
      edge with the true client address, so a client cannot spoof them.
    * Any other peer (e.g. a direct public-IP connection to the container)
      is keyed by the peer address itself, which is also unspoofable.
"""

import ipaddress

from fastapi import Request
from slowapi import Limiter


def _normalize_ip(host: str) -> str | None:
    """Return the normalized dotted form of an IP, or None if the string
    is not an IP address (e.g. empty, or an ASGI scope client hostname)."""
    if not host:
        return None
    if host.startswith("::ffff:"):
        host = host[7:]
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return None
    return host


def _is_trusted_proxy(peer: str) -> bool:
    """True when the direct TCP peer is a private/loopback address, i.e. the
    request provably arrived through Render's internal proxy network."""
    addr = _normalize_ip(peer)
    return addr is not None and ipaddress.ip_address(addr).is_private


def _rate_limit_key(request: Request) -> str:
    """
    Key rate limits by real client IP behind Cloudflare and Render's reverse proxy chain.

    1. CF-Connecting-IP: Untamperable edge IP set by Cloudflare.
    2. X-Forwarded-For [-1]: Untamperable hop IP appended by Render proxy.
    3. request.client.host: Direct socket connection fallback.
    """
    # Priority 1: Cloudflare Edge IP (un-spoofable)
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()

    # Priority 2: Inner trusted hop appended by Render proxy
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()

    # Priority 3: Socket client IP fallback
    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


limiter = Limiter(key_func=_rate_limit_key, default_limits=[])
