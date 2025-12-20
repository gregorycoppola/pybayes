"""
Document routes: /api/docs
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from world.server.deps import get_doc_store, get_run_store


router = APIRouter(prefix="/api/docs", tags=["docs"])


class CreateDocRequest(BaseModel):
    text: str


@router.get("")
async def list_docs(db: int = 0):
    """List all documents."""
    store = get_doc_store(db)
    docs = store.list_all()
    return {
        "docs": [
            {"id": d.id, "text": d.text, "created_at": d.created_at}
            for d in docs
        ]
    }


@router.post("")
async def create_doc(req: CreateDocRequest, db: int = 0):
    """Create a new document."""
    store = get_doc_store(db)
    doc_id = store.add(req.text)
    return {"id": doc_id}


@router.get("/{doc_id}")
async def get_doc(doc_id: str, db: int = 0):
    """Get a document by ID."""
    store = get_doc_store(db)
    doc = store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": doc.id,
        "text": doc.text,
        "created_at": doc.created_at,
    }


@router.get("/{doc_id}/runs")
async def list_doc_runs(doc_id: str, db: int = 0):
    """List all runs for a document."""
    run_store = get_run_store(db)
    runs = run_store.list_for_doc(doc_id)
    return {
        "runs": [r.to_dict() for r in runs]
    }