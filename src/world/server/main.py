"""
QBBN API Server.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

# Import layers to register them
import world.core.layers.base
import world.core.layers.clauses
import world.core.layers.args
import world.core.layers.coref
import world.core.layers.entities
import world.core.layers.link
import world.core.layers.logic
import world.core.layers.ground

# Import routers
from world.server.routes import docs, runs, layers, kbs


def print_routes(app: FastAPI):
    print("\n" + "=" * 60)
    print("QBBN API Routes")
    print("=" * 60)
    
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            methods = ", ".join(route.methods - {"HEAD", "OPTIONS"})
            routes.append((methods, route.path, route.name))
    
    routes.sort(key=lambda r: (r[1], r[0]))
    
    for methods, path, name in routes:
        print(f"  {methods:8} {path:40} → {name}")
    
    print("=" * 60 + "\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print_routes(app)
    yield


app = FastAPI(title="QBBN API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(docs.router)
app.include_router(kbs.router)
app.include_router(runs.router)
app.include_router(layers.router)


@app.get("/")
async def root():
    return {"name": "QBBN API", "version": "0.1.0"}