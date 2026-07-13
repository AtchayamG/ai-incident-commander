"""Small Redis runtime checks shared by health routes and the worker."""

import contextlib
import time
from collections.abc import Callable
from datetime import UTC, datetime

from redis import Redis
from redis.exceptions import RedisError

WORKER_KEY = "incident-commander:worker:heartbeat"
WORKER_TTL_SECONDS = 15


def redis_client(url: str) -> Redis:
    return Redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


def redis_connected(url: str) -> bool:
    client = redis_client(url)
    try:
        return bool(client.ping())
    except RedisError:
        return False
    finally:
        client.close()


def worker_heartbeat(url: str) -> datetime | None:
    client = redis_client(url)
    try:
        value = client.get(WORKER_KEY)
        return datetime.fromisoformat(value) if isinstance(value, str) else None
    except (RedisError, ValueError):
        return None
    finally:
        client.close()


def run_worker(
    url: str,
    *,
    interval_seconds: float = 5,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Publish an expiring heartbeat; Redis failure never creates stale readiness."""
    client = redis_client(url)
    try:
        while True:
            with contextlib.suppress(RedisError):
                client.setex(WORKER_KEY, WORKER_TTL_SECONDS, datetime.now(UTC).isoformat())
            sleep(interval_seconds)
    finally:
        client.close()
