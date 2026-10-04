import time
from typing import Dict, List
from fastapi import Request
from .config import settings
from .errors import AppException

# In-memory sliding window store: ip -> list of timestamps
_REQUEST_TIMESTAMPS: Dict[str, List[float]] = {}

async def check_rate_limit(request: Request):
    """
    In-memory sliding window rate limiter for analysis endpoints.
    Allows up to settings.RATE_LIMIT_PER_MINUTE requests per minute per IP.
    """
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60.0
    limit = settings.RATE_LIMIT_PER_MINUTE

    timestamps = _REQUEST_TIMESTAMPS.get(client_ip, [])
    # Filter timestamps within current window
    valid_timestamps = [t for t in timestamps if now - t < window]

    if len(valid_timestamps) >= limit:
        oldest = valid_timestamps[0]
        retry_after = int(window - (now - oldest)) + 1
        _REQUEST_TIMESTAMPS[client_ip] = valid_timestamps
        raise AppException(
            code="RATE_LIMITED",
            message=f"Rate limit exceeded. Maximum {limit} requests per minute allowed.",
            status_code=429,
            details={
                "limit": limit,
                "window_seconds": 60,
                "retry_after_seconds": max(1, retry_after)
            }
        )

    valid_timestamps.append(now)
    _REQUEST_TIMESTAMPS[client_ip] = valid_timestamps
