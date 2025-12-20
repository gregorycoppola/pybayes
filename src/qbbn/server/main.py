# src/qbbn/server/main.py
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
import qbbn.core.layers.tokens
import qbbn.core.layers.correct
import qbbn.core.layers.segments
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


# === Request/Response Models ===

class CreateDocRequest(BaseModel):
    text: str


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
    """Create a new document."""
    store = get_store(db)
    doc_id = store.add(req.text)
    return {"id": doc_id}


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
            # Parse the override
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
    
    openai_client = OpenAI()
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


@app.put("/api/docs/{doc_id}/layers/{layer_id}")
async def override_layer(doc_id: str, layer_id: str, req: OverrideLayerRequest, db: int = 0):
    """Set a layer override."""
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