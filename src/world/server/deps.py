"""
Shared dependencies for routes.
"""

import redis
from openai import OpenAI

from world.core.document import DocumentStore
from world.core.run import RunStore
from world.core.kb import KBStore


def get_redis(db: int = 0):
    return redis.Redis(host="localhost", port=6379, db=db)


def get_doc_store(db: int = 0) -> DocumentStore:
    return DocumentStore(get_redis(db))


def get_run_store(db: int = 0) -> RunStore:
    return RunStore(get_redis(db))


def get_kb_store(db: int = 0) -> KBStore:
    return KBStore(get_redis(db))


def get_openai() -> OpenAI:
    return OpenAI()