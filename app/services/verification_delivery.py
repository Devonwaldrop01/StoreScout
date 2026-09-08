"""Bounded worker-to-web delivery; a timeout is an unknown write outcome."""
import asyncio
import logging
import httpx
from app.core.index_hold import require_index_writes

logger = logging.getLogger(__name__)
ATTEMPT_DEADLINE_S = 60
TOTAL_DEADLINE_S = 125
RETRY_DELAY_S = 5
MAX_RESPONSE_BYTES = 1024 * 1024


async def deliver(url, payload, headers, *, client=None):
    require_index_writes()
    async def send(active):
        async with asyncio.timeout(TOTAL_DEADLINE_S):
            for attempt in range(2):
                require_index_writes()
                try:
                    # HTTPX's read timeout resets per chunk. This outer timer
                    # also bounds DNS, connection pooling and a dripping body.
                    async with asyncio.timeout(ATTEMPT_DEADLINE_S):
                        async with active.stream("POST", url, json=payload, headers=headers) as response:
                            if response.status_code != 200:
                                break
                            body = bytearray()
                            async for data in response.aiter_bytes():
                                body.extend(data)
                                if len(body) > MAX_RESPONSE_BYTES:
                                    raise ValueError("oversize verification response")
                            import json
                            result = json.loads(body)
                            if not isinstance(result, dict) or result.get("outcome") not in {
                                "verified", "rejected", "failed", "skipped"
                            }:
                                raise ValueError("invalid verification response")
                            return result
                except (httpx.ConnectError, httpx.ConnectTimeout):
                    # Only an undelivered connection failure is safe to retry.
                    # Read/write/total timeouts might already have committed.
                    if attempt:
                        break
                    await asyncio.sleep(RETRY_DELAY_S)
        return None

    try:
        if client is not None:
            result = await send(client)
        else:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=10, pool=5),
                                         follow_redirects=False) as active:
                result = await send(active)
        if result is not None:
            return result
    except (TimeoutError, httpx.HTTPError, ValueError) as exc:
        logger.warning("verification delivery ended for %s (%s); outcome unknown",
                       payload["domain"], type(exc).__name__)
    return {"domain": payload["domain"], "outcome": "failed", "reason": "web_unreachable"}


def verify_via_web(domain, source, source_query, *, endpoint="verify"):
    from app.core.config import get_settings
    settings = get_settings()
    if endpoint not in {"verify", "process"}:
        raise ValueError("invalid index endpoint")
    return asyncio.run(deliver(
        f"{settings.api_internal_url}/api/v1/internal/store-index/{endpoint}",
        {"domain": domain, "source": source, "source_query": source_query},
        {"x-internal-token": settings.internal_secret},
    ))
