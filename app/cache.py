import json
import hashlib
import functools
import redis
from app.config import settings

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


def _make_cache_key(prefix: str, kwargs: dict) -> str:
    """Deterministic cache key from function name + sorted kwargs,
    so /revenue-trends?year=2018 and /revenue-trends?year=2017 don't
    collide, and argument order doesn't matter."""
    kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
    digest = hashlib.md5(kwargs_str.encode()).hexdigest()
    return f"{prefix}:{digest}"


def cached(prefix: str, ttl: int | None = None):
    """Decorator for FastAPI route functions that run expensive
    aggregation queries. Caches the JSON-serializable return value.

    Deliberately NOT caching the DB session object or request object --
    only kwargs that affect the query result (e.g. filters, page number)
    should be passed as cache-relevant. We exclude `db` explicitly.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache_kwargs = {k: v for k, v in kwargs.items() if k != "db"}
            key = _make_cache_key(prefix, cache_kwargs)

             cached_value = redis_client.get(key)
            if cached_value is not None:
                 result = json.loads(cached_value)
                 result["_cache_hit"] = True
                 return result

            result = await func(*args, **kwargs)
            # result is expected to be a dict (Pydantic .model_dump() or plain dict)
            serializable = json.loads(json.dumps(result, default=str))
             redis_client.setex(key, ttl or settings.cache_ttl_seconds, json.dumps(serializable))
             serializable["_cache_hit"] = False
            return serializable
        return wrapper
    return decorator


def invalidate_prefix(prefix: str):
    """Manual cache-busting helper -- call this if you ever reload data
    and want to force endpoints to recompute instead of serving stale
    cached aggregates."""
    for key in redis_client.scan_iter(f"{prefix}:*"):
        redis_client.delete(key)
