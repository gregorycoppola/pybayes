"""
Document routes: /api/docs
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from world.server.deps import get_doc_store, get_run_store, get_openai
from world.core.layers import get_layer
from world.core.layers.runner import run_layer_on_doc


router = APIRouter(prefix="/api/docs", tags=["docs"])


class CreateDocRequest(BaseModel):
    text: str


class RunLayerRequest(BaseModel):
    force: bool = False


class SetLayerRequest(BaseModel):
    dsl: str


# === Document CRUD ===

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
    
    # Include list of computed layers
    stages = store.list_stages(doc_id)
    
    return {
        "id": doc.id,
        "text": doc.text,
        "created_at": doc.created_at,
        "layers": stages,
    }


@router.delete("/{doc_id}")
async def delete_doc(doc_id: str, db: int = 0):
    """Delete a document."""
    store = get_doc_store(db)
    if not store.delete(doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"success": True}


@router.get("/{doc_id}/runs")
async def list_doc_runs(doc_id: str, db: int = 0):
    """List all runs for a document."""
    run_store = get_run_store(db)
    runs = run_store.list_for_doc(doc_id)
    return {
        "runs": [r.to_dict() for r in runs]
    }


# === Layer operations ===

@router.post("/{doc_id}/layers/{layer_id}/run")
async def run_layer(doc_id: str, layer_id: str, req: Optional[RunLayerRequest] = None, db: int = 0):
    """Run a layer on a document."""
    store = get_doc_store(db)
    doc = store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    force = req.force if req else False
    context = {"openai": get_openai()}
    
    result = run_layer_on_doc(store, doc, layer_id, force=force, context=context)
    
    return {
        "layer_id": layer_id,
        "success": result.success,
        "message": result.message,
    }


@router.get("/{doc_id}/layers/{layer_id}")
async def get_layer_data(doc_id: str, layer_id: str, db: int = 0):
    """Get layer data as JSON."""
    store = get_doc_store(db)
    doc = store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    data = store.get_data(doc_id, layer_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Layer {layer_id} not run yet")
    
    return {"layer_id": layer_id, "data": data}


@router.get("/{doc_id}/layers/{layer_id}/dsl")
async def get_layer_dsl(doc_id: str, layer_id: str, db: int = 0):
    """Get layer data as DSL."""
    store = get_doc_store(db)
    doc = store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    data = store.get_data(doc_id, layer_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Layer {layer_id} not run yet")
    
    layer = get_layer(layer_id)
    dsl = layer.format_dsl(data)
    
    return {"layer_id": layer_id, "ext": layer.ext, "dsl": dsl}


@router.put("/{doc_id}/layers/{layer_id}")
async def set_layer_override(doc_id: str, layer_id: str, req: SetLayerRequest, db: int = 0):
    """Set layer data from DSL (override)."""
    store = get_doc_store(db)
    doc = store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    layer = get_layer(layer_id)
    
    try:
        data = layer.parse_dsl(req.dsl)
    except Exception as e:
        return {"success": False, "errors": [f"Parse error: {e}"]}
    
    errors = layer.validate(data)
    if errors:
        return {"success": False, "errors": errors}
    
    store.set_data(doc_id, layer_id, data)
    return {"success": True}


@router.delete("/{doc_id}/layers/{layer_id}/override")
async def clear_layer_override(doc_id: str, layer_id: str, db: int = 0):
    """Clear layer data (will need re-run)."""
    store = get_doc_store(db)
    doc = store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    store.client.delete(store._data_key(doc_id, layer_id))
    return {"success": True}