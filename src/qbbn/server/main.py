"""
QBBN API Server.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

# Import layers to register them
import qbbn.core.layers.base
import qbbn.core.layers.clauses
import qbbn.core.layers.args
import qbbn.core.layers.coref
import qbbn.core.layers.entities
import qbbn.core.layers.link
import qbbn.core.layers.logic
import qbbn.core.layers.ground

# Import routers
from qbbn.server.routes import docs, runs, layers


def print_routes(app: FastAPI):
    """Print all registered routes."""
    print("\n" + "=" * 60)
    print("QBBN API Routes")
    print("=" * 60)
    
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            methods = ", ".join(route.methods - {"HEAD", "OPTIONS"})
            routes.append((methods, route.path, route.name))
    
    # Sort by path
    routes.sort(key=lambda r: (r[1], r[0]))
    
    for methods, path, name in routes:
        print(f"  {methods:8} {path:40} → {name}")
    
    print("=" * 60 + "\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print_routes(app)
    yield
    # Shutdown
    pass


app = FastAPI(title="QBBN API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(docs.router)
app.include_router(runs.router)
app.include_router(layers.router)


@app.get("/")
async def root():
    return {"name": "QBBN API", "version": "0.1.0"}