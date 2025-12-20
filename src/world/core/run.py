"""
Run - a workspace for processing a doc against a KB.
"""

import json
import uuid
from datetime import datetime
from dataclasses import dataclass


@dataclass
class Run:
    id: str
    doc_id: str
    kb_id: str
    parent_run_id: str | None
    created_at: str
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "doc_id": self.doc_id,
            "kb_id": self.kb_id,
            "parent_run_id": self.parent_run_id,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Run":
        return cls(
            id=data["id"],
            doc_id=data["doc_id"],
            kb_id=data["kb_id"],
            parent_run_id=data.get("parent_run_id"),
            created_at=data["created_at"],
        )


class RunStore:
    """Stores runs in Redis."""
    
    def __init__(self, client):
        self.client = client
    
    def _run_key(self, run_id: str) -> str:
        return f"world:run:{run_id}"
    
    def _run_data_key(self, run_id: str, layer_id: str) -> str:
        return f"world:run:{run_id}:data:{layer_id}"
    
    def _doc_runs_key(self, doc_id: str) -> str:
        return f"world:doc:{doc_id}:runs"
    
    def create(self, doc_id: str, kb_id: str, parent_run_id: str | None = None) -> str:
        """Create a new run, returns run_id."""
        run_id = uuid.uuid4().hex[:12]
        
        run = Run(
            id=run_id,
            doc_id=doc_id,
            kb_id=kb_id,
            parent_run_id=parent_run_id,
            created_at=datetime.utcnow().isoformat(),
        )
        
        self.client.set(self._run_key(run_id), json.dumps(run.to_dict()))
        self.client.rpush(self._doc_runs_key(doc_id), run_id)
        
        if parent_run_id:
            self._copy_layer_data(parent_run_id, run_id)
        
        return run_id
    
    def _copy_layer_data(self, from_run_id: str, to_run_id: str):
        pattern = f"world:run:{from_run_id}:data:*"
        for key in self.client.scan_iter(match=pattern):
            layer_id = key.decode().split(":")[-1]
            data = self.client.get(key)
            if data:
                self.client.set(self._run_data_key(to_run_id, layer_id), data)
    
    def get(self, run_id: str) -> Run | None:
        data = self.client.get(self._run_key(run_id))
        if not data:
            return None
        return Run.from_dict(json.loads(data))
    
    def list_for_doc(self, doc_id: str) -> list[Run]:
        run_ids = self.client.lrange(self._doc_runs_key(doc_id), 0, -1)
        runs = []
        for rid in run_ids:
            run = self.get(rid.decode())
            if run:
                runs.append(run)
        return runs
    
    def get_data(self, run_id: str, layer_id: str) -> dict | None:
        data = self.client.get(self._run_data_key(run_id, layer_id))
        if not data:
            return None
        return json.loads(data)
    
    def set_data(self, run_id: str, layer_id: str, data: dict):
        self.client.set(self._run_data_key(run_id, layer_id), json.dumps(data))
    
    def has_data(self, run_id: str, layer_id: str) -> bool:
        return self.client.exists(self._run_data_key(run_id, layer_id))
    
    def delete_data(self, run_id: str, layer_id: str):
        self.client.delete(self._run_data_key(run_id, layer_id))