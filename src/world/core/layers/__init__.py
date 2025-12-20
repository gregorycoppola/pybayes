# src/world/core/layers/__init__.py
"""
Layer-based processing architecture.

Each layer:
  - Has a unique string ID
  - Declares dependencies on other layers
  - Has a DSL file extension
  - Can process inputs → data
  - Can parse/format its DSL
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class LayerResult:
    success: bool
    data: Any
    message: str = ""


class Layer(ABC):
    """Base class for all layers."""
    
    id: str  # unique identifier
    depends_on: list[str] = []  # layer ids this depends on
    ext: str = ".txt"  # DSL file extension
    
    @abstractmethod
    def process(self, inputs: dict[str, Any], context: dict) -> LayerResult:
        """
        Process inputs from dependency layers.
        
        Args:
            inputs: {layer_id: data} for each dependency
            context: shared context (openai client, etc)
        
        Returns:
            LayerResult with processed data
        """
        pass
    
    @abstractmethod
    def parse_dsl(self, text: str) -> Any:
        """Parse DSL text into data."""
        pass
    
    @abstractmethod
    def format_dsl(self, data: Any) -> str:
        """Format data as DSL text."""
        pass
    
    def validate(self, data: Any) -> list[str]:
        """Validate data, return list of errors."""
        return []


# Layer registry
LAYERS: dict[str, Layer] = {}


def register_layer(layer: Layer) -> Layer:
    """Register a layer instance."""
    LAYERS[layer.id] = layer
    return layer


def get_layer(layer_id: str) -> Layer:
    if layer_id not in LAYERS:
        available = ", ".join(LAYERS.keys())
        raise ValueError(f"Unknown layer: {layer_id}. Available: {available}")
    return LAYERS[layer_id]


def list_layers() -> list[str]:
    return list(LAYERS.keys())


def resolve_dependencies(layer_ids: list[str]) -> list[str]:
    """
    Topological sort: return all layers needed, in execution order.
    """
    needed = set()
    order = []
    
    def visit(lid: str):
        if lid in needed:
            return
        layer = get_layer(lid)
        for dep in layer.depends_on:
            visit(dep)
        needed.add(lid)
        order.append(lid)
    
    for lid in layer_ids:
        visit(lid)
    
    return order