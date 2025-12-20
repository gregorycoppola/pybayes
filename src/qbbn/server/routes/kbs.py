"""
Knowledge Base routes: /api/kbs
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from qbbn.server.deps import get_kb_store


router = APIRouter(prefix="/api/kbs", tags=["kbs"])


class CreateKBRequest(BaseModel):
    name: str
    dsl: str


@router.get("")
async def list_kbs(db: int = 0):
    """List all knowledge bases."""
    store = get_kb_store(db)
    kbs = store.list_all()
    return {
        "kbs": [
            {"id": kb.id, "name": kb.name, "created_at": kb.created_at,
             "entity_count": len(kb.entities), "fact_count": len(kb.facts), "rule_count": len(kb.rules)}
            for kb in kbs
        ]
    }


@router.post("")
async def create_kb(req: CreateKBRequest, db: int = 0):
    """Create a new knowledge base from DSL."""
    store = get_kb_store(db)
    try:
        kb_id = store.create(req.name, req.dsl)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    kb = store.get(kb_id)
    return {
        "id": kb.id,
        "name": kb.name,
        "entity_count": len(kb.entities),
        "fact_count": len(kb.facts),
        "rule_count": len(kb.rules),
    }


@router.get("/{kb_id}")
async def get_kb(kb_id: str, db: int = 0):
    """Get a knowledge base by ID."""
    store = get_kb_store(db)
    kb = store.get(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb.to_dict()


@router.get("/{kb_id}/dsl")
async def get_kb_dsl(kb_id: str, db: int = 0):
    """Get knowledge base as DSL text."""
    store = get_kb_store(db)
    kb = store.get(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return {"id": kb_id, "name": kb.name, "dsl": kb.to_dsl()}


@router.delete("/{kb_id}")
async def delete_kb(kb_id: str, db: int = 0):
    """Delete a knowledge base."""
    store = get_kb_store(db)
    store.delete(kb_id)
    return {"deleted": kb_id}