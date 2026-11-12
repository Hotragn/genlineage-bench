"""Hand-written HTTP retry policy built from generated settings."""
from app import settings


def backoff_schedule():
    """Seconds to wait before each retry: 1, 2, 4, ... for settings.RETRIES retries."""
    return [2 ** i for i in range(settings.RETRIES)]


def cache_enabled():
    return bool(settings.USE_CACHE) and not settings.DEBUG
