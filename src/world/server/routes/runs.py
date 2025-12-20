"""
Run routes: /api/runs
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from world.core.layers import list_layers, get_layer
from world.core.layers.runner import LayerRunner
from world.server.deps import get_doc_store, get_run_store, get_kb_store, get_openai


router = APIRouter(prefix="/api/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    doc_id: str
    kb_id: str
    parent_run_id: str | None = None


class ProcessRunRequest(BaseModel):
    layers: list[str] | None = None
    force: bool = False


@router.post("")
async def create_run(req: CreateRunRequest, db: int = 0):
    """Create a new annotation run."""
    doc_store = get_doc_store(db)
    run_store = get_run_store(db)
    kb_store = get_kb_store(db)
    
    doc = doc_store.get(req.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    kb = kb_store.get(req.kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    if req.parent_run_id:
        parent = run_store.get(req.parent_run_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent run not found")
    
    run_id = run_store.create(req.doc_id, req.kb_id, req.parent_run_id)
    run = run_store.get(run_id)
    
    return run.to_dict()


@router.get("/{run_id}")
async def get_run(run_id: str, db: int = 0):
    """Get a run with all layer status."""
    doc_store = get_doc_store(db)
    run_store = get_run_store(db)
    kb_store = get_kb_store(db)
    
    run = run_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    doc = doc_store.get(run.doc_id)
    kb = kb_store.get(run.kb_id)
    
    layers = {}
    for lid in list_layers():
        data = run_store.get_data(run_id, lid)
        layers[lid] = {
            "status": "done" if data else "pending",
            "data": data,
        }
    
    return {
        **run.to_dict(),
        "doc_text": doc.text if doc else None,
        "kb_name": kb.name if kb else None,
        "layers": layers,
    }


@router.post("/{run_id}/process")
async def process_run(run_id: str, req: ProcessRunRequest = None, db: int = 0):
    """Process a run (execute layers)."""
    doc_store = get_doc_store(db)
    run_store = get_run_store(db)
    kb_store = get_kb_store(db)
    
    run = run_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    kb = kb_store.get(run.kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    openai_client = get_openai()
    runner = LayerRunner(doc_store, run_store, kb_store, {"openai": openai_client})
    
    if req and req.layers:
        layer_ids = req.layers
    else:
        layer_ids = list_layers()
    
    force = req.force if req else False
    results = runner.run(run_id, layer_ids, force=force)
    
    return {
        "run_id": run_id,
        "results": {
            lid: {"success": r.success, "message": r.message}
            for lid, r in results.items()
        }
    }


@router.get("/{run_id}/layers/{layer_id}/dsl")
async def get_run_layer_dsl(run_id: str, layer_id: str, db: int = 0):
    """Get layer data as DSL text."""
    doc_store = get_doc_store(db)
    run_store = get_run_store(db)
    kb_store = get_kb_store(db)
    
    runner = LayerRunner(doc_store, run_store, kb_store, {})
    dsl = runner.get_dsl(run_id, layer_id)
    
    if dsl is None:
        raise HTTPException(status_code=404, detail=f"No data for layer '{layer_id}'")
    
    layer = get_layer(layer_id)
    return {
        "layer_id": layer_id,
        "ext": layer.ext,
        "dsl": dsl,
    }