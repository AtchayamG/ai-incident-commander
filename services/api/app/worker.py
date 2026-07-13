"""Lightweight local worker process."""

from app.config import Settings
from app.runtime import run_worker


def main() -> None:
    settings = Settings.from_env()
    if not settings.redis_url:
        raise SystemExit("REDIS_URL is required")
    run_worker(settings.redis_url)


if __name__ == "__main__":
    main()
