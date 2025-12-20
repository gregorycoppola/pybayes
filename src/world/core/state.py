# src/world/core/state.py
"""
Global state stored in Redis.
"""

import redis


STATE_KEY = "world:state:namespace"
DEFAULT_NAMESPACE = "default"


def get_namespace(client: redis.Redis) -> str:
    value = client.get(STATE_KEY)
    if value is None:
        return DEFAULT_NAMESPACE
    return value.decode()


def set_namespace(client: redis.Redis, namespace: str) -> None:
    client.set(STATE_KEY, namespace)