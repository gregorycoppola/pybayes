# src/qbbn/server/main.py
"""
FastAPI server for QBBN document viewer.
"""

import redis
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

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


app = FastAPI(title="QBBN Viewer")

# Setup paths
SERVER_DIR = Path(__file__).parent
TEMPLATES_DIR = SERVER_DIR / "templates"
STATIC_DIR = SERVER_DIR / "static"

# Create dirs if needed
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def get_store(db: int = 0) -> DocumentStore:
    client = redis.Redis(host="localhost", port=6379, db=db)
    return DocumentStore(client)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: int = 0):
    """List all documents."""
    store = get_store(db)
    docs = store.list_all()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "docs": docs,
        "db": db,
    })


@app.get("/doc/{doc_id}", response_class=HTMLResponse)
async def view_doc(request: Request, doc_id: str, db: int = 0):
    """View a document with all its layers."""
    store = get_store(db)
    doc = store.get(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    runner = LayerRunner(store, {})
    
    # Get all layer data
    layers_data = []
    for lid in list_layers():
        layer = get_layer(lid)
        dsl = runner.get_dsl(doc_id, lid)
        layers_data.append({
            "id": lid,
            "ext": layer.ext,
            "depends_on": layer.depends_on,
            "dsl": dsl,
            "has_data": dsl is not None,
        })
    
    return templates.TemplateResponse("doc.html", {
        "request": request,
        "doc": doc,
        "layers": layers_data,
        "db": db,
    })


@app.get("/doc/{doc_id}/layer/{layer_id}", response_class=HTMLResponse)
async def view_layer(request: Request, doc_id: str, layer_id: str, db: int = 0):
    """Get a single layer partial (for HTMX)."""
    store = get_store(db)
    runner = LayerRunner(store, {})
    
    layer = get_layer(layer_id)
    dsl = runner.get_dsl(doc_id, layer_id)
    
    return templates.TemplateResponse("layer_partial.html", {
        "request": request,
        "doc_id": doc_id,
        "layer": {
            "id": layer_id,
            "ext": layer.ext,
            "dsl": dsl,
            "has_data": dsl is not None,
        },
        "db": db,
    })


@app.post("/doc/{doc_id}/run/{layer_id}", response_class=HTMLResponse)
async def run_layer(request: Request, doc_id: str, layer_id: str, db: int = 0):
    """Run a layer (for HTMX)."""
    from openai import OpenAI
    
    store = get_store(db)
    openai_client = OpenAI()
    runner = LayerRunner(store, {"openai": openai_client})
    
    results = runner.run(doc_id, [layer_id], force=True)
    result = results.get(layer_id)
    
    layer = get_layer(layer_id)
    dsl = runner.get_dsl(doc_id, layer_id)
    
    return templates.TemplateResponse("layer_partial.html", {
        "request": request,
        "doc_id": doc_id,
        "layer": {
            "id": layer_id,
            "ext": layer.ext,
            "dsl": dsl,
            "has_data": dsl is not None,
            "message": result.message if result else None,
        },
        "db": db,
    })