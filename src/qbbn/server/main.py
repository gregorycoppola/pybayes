"""
FastAPI JSON API for QBBN.
"""

import redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

from qbbn.core.document import DocumentStore
from qbbn.core.layers import list_layers, get_layer
from qbbn.core.layers.runner import LayerRunner

# Import all layers to register them
import qbbn.core.layers.base
import qbbn.core.layers.clauses
import qbbn.core.layers.args
import qbbn.core.layers.coref
import qbbn.core.layers.logic
import qbbn.core.layers.ground


app = FastAPI(title="QBBN API")

# CORS for local SolidJS dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_store(db: int = 0) -> DocumentStore:
    client = redis.Redis(host="localhost", port=6379, db=db)
    return DocumentStore(client)


def get_openai() -> OpenAI:
    return OpenAI()


# === Request/Response Models ===

class CreateDocRequest(BaseModel):
    text: str
    run_base: bool = True  # Auto-run base layer by default


class RunLayerRequest(BaseModel):
    force: bool = False


class OverrideLayerRequest(BaseModel):
    dsl: str


# === Routes ===

@app.get("/api/layers")
async def list_all_layers():
    """List all registered layers."""
    layers = []
    for lid in list_layers():
        layer = get_layer(lid)
        layers.append({
            "id": lid,
            "ext": layer.ext,
            "depends_on": layer.depends_on,
        })
    return {"layers": layers}


@app.get("/api/docs")
async def list_docs(db: int = 0):
    """List all documents."""
    store = get_store(db)
    docs = store.list_all()
    return {
        "docs": [
            {"id": d.id, "text": d.text, "created_at": d.created_at}
            for d in docs
        ]
    }


@app.post("/api/docs")
async def create_doc(req: CreateDocRequest, db: int = 0):
    """Create a new document. Auto-runs base layer by default."""
    store = get_store(db)
    doc_id = store.add(req.text)
    
    result = {"id": doc_id}
    
    # Auto-run base layer
    if req.run_base:
        openai_client = get_openai()
        runner = LayerRunner(store, {"openai": openai_client})
        results = runner.run(doc_id, ["base"], force=False)
        
        base_result = results.get("base")
        if base_result:
            result["base"] = {
                "success": base_result.success,
                "message": base_result.message,
            }
    
    return result


@app.get("/api/docs/{doc_id}")
async def get_doc(doc_id: str, db: int = 0):
    """Get a document with all layer data."""
    store = get_store(db)
    doc = store.get(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Build layers dict
    layers = {}
    for lid in list_layers():
        data = store.get_data(doc_id, lid)
        override = store.get_data(doc_id, f"{lid}_override")
        
        if data is not None:
            status = "done"
        elif override is not None:
            status = "override"
            layer = get_layer(lid)
            try:
                data = layer.parse_dsl(override)
            except:
                data = None
                status = "error"
        else:
            status = "pending"
        
        layers[lid] = {
            "status": status,
            "data": data,
            "has_override": override is not None,
        }
    
    return {
        "id": doc.id,
        "text": doc.text,
        "created_at": doc.created_at,
        "layers": layers,
    }


@app.post("/api/docs/{doc_id}/layers/{layer_id}/run")
async def run_layer(doc_id: str, layer_id: str, req: RunLayerRequest = None, db: int = 0):
    """Run a layer on a document."""
    store = get_store(db)
    doc = store.get(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        get_layer(layer_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    openai_client = get_openai()
    runner = LayerRunner(store, {"openai": openai_client})
    
    force = req.force if req else False
    results = runner.run(doc_id, [layer_id], force=force)
    
    result = results.get(layer_id)
    data = store.get_data(doc_id, layer_id)
    
    return {
        "layer_id": layer_id,
        "success": result.success if result else False,
        "message": result.message if result else "unknown error",
        "data": data,
    }


@app.post("/api/docs/{doc_id}/run")
async def run_all_layers(doc_id: str, db: int = 0):
    """Run all layers on a document."""
    store = get_store(db)
    doc = store.get(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    openai_client = get_openai()
    runner = LayerRunner(store, {"openai": openai_client})
    
    # Run all layers
    all_layer_ids = list_layers()
    results = runner.run(doc_id, all_layer_ids, force=False)
    
    return {
        "doc_id": doc_id,
        "results": {
            lid: {
                "success": r.success,
                "message": r.message,
            }
            for lid, r in results.items()
        }
    }


@app.get("/api/docs/{doc_id}/layers/{layer_id}/dsl")
async def get_layer_dsl(doc_id: str, layer_id: str, db: int = 0):
    """Get layer data as DSL text."""
    store = get_store(db)
    runner = LayerRunner(store, {})
    
    dsl = runner.get_dsl(doc_id, layer_id)
    
    if dsl is None:
        raise HTTPException(status_code=404, detail=f"No data for layer '{layer_id}'")
    
    layer = get_layer(layer_id)
    return {
        "layer_id": layer_id,
        "ext": layer.ext,
        "dsl": dsl,
    }


@app.put("/api/docs/{doc_id}/layers/{layer_id}")
async def override_layer(doc_id: str, layer_id: str, req: OverrideLayerRequest, db: int = 0):
    """Set a layer override from DSL."""
    store = get_store(db)
    doc = store.get(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    runner = LayerRunner(store, {})
    errors = runner.set_override(doc_id, layer_id, req.dsl)
    
    if errors:
        return {"success": False, "errors": errors}
    
    return {"success": True}


@app.delete("/api/docs/{doc_id}/layers/{layer_id}/override")
async def clear_override(doc_id: str, layer_id: str, db: int = 0):
    """Clear a layer override."""
    store = get_store(db)
    store.delete_data(doc_id, f"{layer_id}_override")
    return {"success": True}