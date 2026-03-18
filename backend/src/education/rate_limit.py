"""Simple in-memory rate limiting for education APIs."""

import time
from collections import defaultdict

from fastapi import Depends, HTTPException, Request

from .rbac import get_actor_context
from .schemas import ActorContext

_WINDOW_SECONDS = 60
_COUNTERS: dict[str, list[float]] = defaultdict(list)


def make_rate_limiter(action: str, limit: int = 120):
    async def _limit(
        request: Request,
        actor: ActorContext = Depends(get_actor_context),
    ):
        now = time.time()
        key = f"{action}:{actor.org_id}:{actor.user_id}:{request.client.host if request.client else 'unknown'}"
        history = _COUNTERS[key]
        cutoff = now - _WINDOW_SECONDS
        history[:] = [t for t in history if t >= cutoff]
        if len(history) >= limit:
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded for {action}")
        history.append(now)
        return None

    _limit.__name__ = f"rate_limit_{action.replace(':', '_')}"
    return _limit
