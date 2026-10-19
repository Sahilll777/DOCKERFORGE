import os

import redis


REDIS_URL = os.environ["REDIS_URL"]
CACHE_TTL_SECONDS = 30
REDIS_CONNECT_TIMEOUT_SECONDS = 2
REDIS_SOCKET_TIMEOUT_SECONDS = 2


def get_redis_client():
    return redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=REDIS_CONNECT_TIMEOUT_SECONDS,
        socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
        retry_on_timeout=False,
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
