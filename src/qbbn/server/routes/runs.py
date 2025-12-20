"""
Run routes: /api/runs
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from qbbn.core.layers import list_layers, get_layer
from qbbn.core.layers.runner import LayerRunner
from qbbn.server.deps import get_doc_store, get_run_store, get_openai


router = APIRouter(prefix="/api/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    doc_id: str
    kb_path: str = "kb"
    parent_run_id: str | None = None


class ProcessRunRequest(BaseModel):
    layers: list[str] | None = None
    force: bool = False


@router.post("")
async def create_run(req: CreateRunRequest, db: int = 0):
    """Create a new annotation run."""
    doc_store = get_doc_store(db)
    run_store = get_run_store(db)
    
    doc = doc_store.get(req.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if req.parent_run_id:
        parent = run_store.get(req.parent_run_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent run not found")
    
    run_id = run_store.create(req.doc_id, req.kb_path, req.parent_run_id)
    run = run_store.get(run_id)
    
    return run.to_dict()


@router.get("/{run_id}")
async def get_run(run_id: str, db: int = 0):
    """Get a run with all layer status."""
    doc_store = get_doc_store(db)
    run_store = get_run_store(db)
    
    run = run_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    doc = doc_store.get(run.doc_id)
    
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
        "layers": layers,
    }


@router.post("/{run_id}/process")
async def process_run(run_id: str, req: ProcessRunRequest = None, db: int = 0):
    """Process a run (execute layers)."""
    doc_store = get_doc_store(db)
    run_store = get_run_store(db)
    
    run = run_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    openai_client = get_openai()
    runner = LayerRunner(doc_store, run_store, {"openai": openai_client})
    
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
    
    runner = LayerRunner(doc_store, run_store, {})
    dsl = runner.get_dsl(run_id, layer_id)
    
    if dsl is None:
        raise HTTPException(status_code=404, detail=f"No data for layer '{layer_id}'")
    
    layer = get_layer(layer_id)
    return {
        "layer_id": layer_id,
        "ext": layer.ext,
        "dsl": dsl,
    }