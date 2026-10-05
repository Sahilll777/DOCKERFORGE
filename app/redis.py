import os

import redis


REDIS_URL = os.environ["REDIS_URL"]
CACHE_TTL_SECONDS = 30


def get_redis_client():
    return redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
    )


def check_redis_connection():
    client = get_redis_client()
    return client.ping()


def get_cached_value(key):
    client = get_redis_client()
    return client.get(key)


def set_cached_value(key, value):
    client = get_redis_client()
    client.setex(
        key,
        CACHE_TTL_SECONDS,
        value,
    )
