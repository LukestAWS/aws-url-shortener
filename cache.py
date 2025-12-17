import os
from typing import Optional
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
TTL = 86400  # 24 hours

def get_long_from_cache(short_code: str) -> Optional[str]:
    return client.get(f"short:{short_code}")

def get_short_from_cache(long_url: str) -> Optional[str]:
    return client.get(f"long:{long_url}")

def set_cache(short_code: str, long_url: str):
    client.set(f"short:{short_code}", long_url, ex=TTL)
    client.set(f"long:{long_url}", short_code, ex=TTL)
