"""
Layer routes: /api/layers
"""

from fastapi import APIRouter

from qbbn.core.layers import list_layers, get_layer


router = APIRouter(prefix="/api/layers", tags=["layers"])


@router.get("")
async def get_all_layers():
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