"""
FastAPI JSON API for QBBN.
"""

import redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

from qbbn.core.document import DocumentStore
from qbbn.core.run import RunStore
from qbbn.core.layers import list_layers, get_layer
from qbbn.core.layers.runner import LayerRunner

# Import all layers to register them
import qbbn.core.layers.base
import qbbn.core.layers.clauses
import qbbn.core.layers.args
import qbbn.core.layers.coref
import qbbn.core.layers.entities
import qbbn.core.layers.link
import qbbn.core.layers.logic
import qbbn.core.layers.ground


app = FastAPI(title="QBBN API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_redis(db: int = 0):
    return redis.Redis(host="localhost", port=6379, db=db)


def get_doc_store(db: int = 0) -> DocumentStore:
    return DocumentStore(get_redis(db))


def get_run_store(db: int = 0) -> RunStore:
    return RunStore(get_redis(db))


def get_openai() -> OpenAI:
    return OpenAI()


# === Request Models ===

class CreateDocRequest(BaseModel):
    text: str


class CreateRunRequest(BaseModel):
    doc_id: str
    kb_path: str = "kb"
    parent_run_id: str | None = None


class ProcessRunRequest(BaseModel):
    layers: list[str] | None = None
    force: bool = False


# === Doc Routes ===

@app.get("/api/docs")
async def api_list_docs(db: int = 0):
    store = get_doc_store(db)
    docs = store.list_all()
    return {
        "docs": [
            {"id": d.id, "text": d.text, "created_at": d.created_at}
            for d in docs
        ]
    }


@app.post("/api/docs")
async def api_create_doc(req: CreateDocRequest, db: int = 0):
    store = get_doc_store(db)
    doc_id = store.add(req.text)
    return {"id": doc_id}


@app.get("/api/docs/{doc_id}")
async def api_get_doc(doc_id: str, db: int = 0):
    store = get_doc_store(db)
    doc = store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": doc.id,
        "text": doc.text,
        "created_at": doc.created_at,
    }


@app.get("/api/docs/{doc_id}/runs")
async def api_list_doc_runs(doc_id: str, db: int = 0):
    run_store = get_run_store(db)
    runs = run_store.list_for_doc(doc_id)
    return {
        "runs": [r.to_dict() for r in runs]
    }


# === Run Routes ===

@app.post("/api/runs")
async def api_create_run(req: CreateRunRequest, db: int = 0):
    doc_store = get_doc_store(db)
    run_store = get_run_store(db)
    
    # Verify doc exists
    doc = doc_store.get(req.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Verify parent run if specified
    if req.parent_run_id:
        parent = run_store.get(req.parent_run_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent run not found")
    
    run_id = run_store.create(req.doc_id, req.kb_path, req.parent_run_id)
    run = run_store.get(run_id)
    
    return run.to_dict()


@app.get("/api/runs/{run_id}")
async def api_get_run(run_id: str, db: int = 0):
    doc_store = get_doc_store(db)
    run_store = get_run_store(db)
    
    run = run_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    doc = doc_store.get(run.doc_id)
    
    # Build layers status
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


@app.post("/api/runs/{run_id}/process")
async def api_process_run(run_id: str, req: ProcessRunRequest = None, db: int = 0):
    doc_store = get_doc_store(db)
    run_store = get_run_store(db)
    
    run = run_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    openai_client = get_openai()
    runner = LayerRunner(doc_store, run_store, {"openai": openai_client})
    
    # Which layers to run
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


@app.get("/api/runs/{run_id}/layers/{layer_id}/dsl")
async def api_get_run_layer_dsl(run_id: str, layer_id: str, db: int = 0):
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


# === Layer Info ===

@app.get("/api/layers")
async def api_list_layers():
    layers = []
    for lid in list_layers():
        layer = get_layer(lid)
        layers.append({
            "id": lid,
            "ext": layer.ext,
            "depends_on": layer.depends_on,
        })
    return {"layers": layers}