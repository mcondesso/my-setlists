"""Shared API rate limiter.

Uses slowapi's default in-memory storage, which is per-process: with more
than one worker or container each has its own counters. Move to a shared
backend (``Limiter(storage_uri="redis://...")``) when the app runs more
than one process.

``get_remote_address`` reads ``request.client.host``. Behind a proxy or load
balancer every request looks like it comes from the proxy, so the deployment
must pass the real client IP through (uvicorn ``--forwarded-allow-ips`` plus
Starlette's ``ProxyHeadersMiddleware``) for per-client limiting to work.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.config import settings

# Disabled under the test environment so the suite is not throttled; the
# rate-limit behaviour itself is covered by test_login_is_rate_limited.
limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.ENVIRONMENT != "test",
)

LOGIN_RATE_LIMIT = "5/minute"
