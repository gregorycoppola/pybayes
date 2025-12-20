# src/qbbn/core/document.py
"""
Document storage and retrieval.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime

import redis

from qbbn.core.state import get_namespace


def generate_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class Document:
    id: str
    text: str
    created_at: str
    namespace: str


class DocumentStore:
    def __init__(self, client: redis.Redis):
        self.client = client
    
    @property
    def namespace(self) -> str:
        return get_namespace(self.client)
    
    def _doc_key(self, doc_id: str) -> str:
        return f"{self.namespace}:doc:{doc_id}"
    
    def _index_key(self) -> str:
        return f"{self.namespace}:doc_index"
    
    def _data_key(self, doc_id: str, stage: str) -> str:
        return f"{self.namespace}:doc:{doc_id}:data:{stage}"
    
    def add(self, text: str) -> str:
        doc_id = generate_id()
        doc = {
            "id": doc_id,
            "text": text,
            "created_at": datetime.utcnow().isoformat(),
            "namespace": self.namespace,
        }
        self.client.set(self._doc_key(doc_id), json.dumps(doc))
        self.client.sadd(self._index_key(), doc_id)
        return doc_id
    
    def get(self, doc_id: str) -> Document | None:
        data = self.client.get(self._doc_key(doc_id))
        if data is None:
            return None
        d = json.loads(data.decode())
        return Document(**d)
    
    def list_all(self) -> list[Document]:
        doc_ids = self.client.smembers(self._index_key())
        docs = []
        for doc_id in doc_ids:
            doc = self.get(doc_id.decode())
            if doc:
                docs.append(doc)
        return sorted(docs, key=lambda d: d.created_at, reverse=True)
    
    def search(self, query: str) -> list[Document]:
        query_lower = query.lower()
        return [d for d in self.list_all() if query_lower in d.text.lower()]
    
    def delete(self, doc_id: str) -> bool:
        if not self.client.exists(self._doc_key(doc_id)):
            return False
        self.client.delete(self._doc_key(doc_id))
        self.client.srem(self._index_key(), doc_id)
        # Delete all data keys
        pattern = f"{self.namespace}:doc:{doc_id}:data:*"
        for key in self.client.scan_iter(pattern):
            self.client.delete(key)
        return True
    
    # Data storage for processors
    def set_data(self, doc_id: str, stage: str, data: any) -> None:
        self.client.set(self._data_key(doc_id, stage), json.dumps(data))
    
    def get_data(self, doc_id: str, stage: str) -> any:
        data = self.client.get(self._data_key(doc_id, stage))
        if data is None:
            return None
        return json.loads(data.decode())
    
    def has_data(self, doc_id: str, stage: str) -> bool:
        return self.client.exists(self._data_key(doc_id, stage))
    
    def list_stages(self, doc_id: str) -> list[str]:
        pattern = f"{self.namespace}:doc:{doc_id}:data:*"
        stages = []
        for key in self.client.scan_iter(pattern):
            stage = key.decode().split(":data:")[-1]
            stages.append(stage)
        return sorted(stages)