# src/qbbn/core/layers/runner.py
"""
Layer execution runner.
"""

from typing import Any
from qbbn.core.layers import Layer, get_layer, resolve_dependencies, LayerResult


class LayerRunner:
    """Runs layers on documents."""
    
    def __init__(self, store, context: dict = None):
        """
        Args:
            store: DocumentStore for persistence
            context: shared context (openai client, etc)
        """
        self.store = store
        self.context = context or {}
    
    def run(self, doc_id: str, layer_ids: list[str], force: bool = False) -> dict[str, LayerResult]:
        """
        Run specified layers on a document.
        
        Args:
            doc_id: document ID
            layer_ids: layers to run (dependencies auto-resolved)
            force: re-run even if cached
        
        Returns:
            {layer_id: LayerResult} for each layer run
        """
        # Resolve dependencies
        all_layers = resolve_dependencies(layer_ids)
        
        results = {}
        
        for lid in all_layers:
            layer = get_layer(lid)
            
            # Check for user override
            override = self.store.get_data(doc_id, f"{lid}_override")
            if override is not None:
                try:
                    data = layer.parse_dsl(override)
                    results[lid] = LayerResult(True, data, "from override")
                    self.store.set_data(doc_id, lid, data)
                    continue
                except Exception as e:
                    results[lid] = LayerResult(False, None, f"override parse error: {e}")
                    continue
            
            # Check cache
            if not force and self.store.has_data(doc_id, lid):
                data = self.store.get_data(doc_id, lid)
                results[lid] = LayerResult(True, data, "cached")
                continue
            
            # Gather inputs
            inputs = {}
            missing = []
            for dep in layer.depends_on:
                if self.store.has_data(doc_id, dep):
                    inputs[dep] = self.store.get_data(doc_id, dep)
                else:
                    missing.append(dep)
            
            if missing:
                results[lid] = LayerResult(False, None, f"missing deps: {missing}")
                continue
            
            # Also pass raw doc
            doc = self.store.get(doc_id)
            if doc:
                inputs["_doc"] = doc
            
            # Run layer
            try:
                result = layer.process(inputs, self.context)
                if result.success:
                    self.store.set_data(doc_id, lid, result.data)
                results[lid] = result
            except Exception as e:
                results[lid] = LayerResult(False, None, f"error: {e}")
        
        return results
    
    def get_dsl(self, doc_id: str, layer_id: str) -> str | None:
        """Get layer data formatted as DSL."""
        layer = get_layer(layer_id)
        data = self.store.get_data(doc_id, layer_id)
        if data is None:
            return None
        return layer.format_dsl(data)
    
    def set_override(self, doc_id: str, layer_id: str, dsl_text: str) -> list[str]:
        """
        Set a user override for a layer.
        
        Returns list of validation errors (empty if valid).
        """
        layer = get_layer(layer_id)
        
        try:
            data = layer.parse_dsl(dsl_text)
        except Exception as e:
            return [f"parse error: {e}"]
        
        errors = layer.validate(data)
        if errors:
            return errors
        
        # Store override
        self.store.set_data(doc_id, f"{layer_id}_override", dsl_text)
        
        # Invalidate downstream
        self._invalidate_downstream(doc_id, layer_id)
        
        return []
    
    def _invalidate_downstream(self, doc_id: str, layer_id: str):
        """Invalidate all layers that depend on this one."""
        from qbbn.core.layers import LAYERS
        
        for lid, layer in LAYERS.items():
            if layer_id in layer.depends_on:
                self.store.delete_data(doc_id, lid)
                self._invalidate_downstream(doc_id, lid)