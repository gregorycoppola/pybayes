# src/world/core/layers/runner.py
"""
Layer execution runner.

Two modes:
- run_layer_on_doc: for doc-level layers (base, clauses, args, coref)
- LayerRunner: for run-level layers that need a KB (ground, logic)
"""

from world.core.layers import get_layer, resolve_dependencies, LayerResult


def run_layer_on_doc(doc_store, doc, layer_id: str, force: bool = False, context: dict = None) -> LayerResult:
    """
    Run a single layer (and its dependencies) on a document.
    
    For doc-level layers that don't need a KB.
    Data is stored in doc_store.
    """
    from world.server.deps import get_openai
    
    if context is None:
        context = {"openai": get_openai()}
    
    all_layers = resolve_dependencies([layer_id])
    
    for lid in all_layers:
        layer = get_layer(lid)
        
        # Check cache
        if not force and doc_store.has_data(doc.id, lid):
            if lid == layer_id:
                data = doc_store.get_data(doc.id, lid)
                return LayerResult(True, data, "cached")
            continue
        
        # Gather inputs from dependencies
        inputs = {"_doc": doc}
        missing = []
        for dep in layer.depends_on:
            if doc_store.has_data(doc.id, dep):
                inputs[dep] = doc_store.get_data(doc.id, dep)
            else:
                missing.append(dep)
        
        if missing:
            if lid == layer_id:
                return LayerResult(False, None, f"missing deps: {missing}")
            continue
        
        # Run layer
        try:
            result = layer.process(inputs, context)
            if result.success:
                doc_store.set_data(doc.id, lid, result.data)
            if lid == layer_id:
                return result
        except Exception as e:
            if lid == layer_id:
                return LayerResult(False, None, f"error: {e}")
    
    return LayerResult(False, None, "layer not found")


class LayerRunner:
    """Runs layers on a run workspace (doc + KB)."""
    
    def __init__(self, doc_store, run_store, kb_store=None, context: dict = None):
        self.doc_store = doc_store
        self.run_store = run_store
        self.kb_store = kb_store
        self.context = context or {}
    
    def run(self, run_id: str, layer_ids: list[str], force: bool = False) -> dict[str, LayerResult]:
        """Run specified layers on a run workspace."""
        run = self.run_store.get(run_id)
        if not run:
            return {"_error": LayerResult(False, None, "run not found")}
        
        # Load KB and add to context
        if self.kb_store:
            kb = self.kb_store.get(run.kb_id)
            if kb:
                self.context["kb"] = kb
        
        all_layers = resolve_dependencies(layer_ids)
        
        results = {}
        
        for lid in all_layers:
            layer = get_layer(lid)
            
            if not force and self.run_store.has_data(run_id, lid):
                data = self.run_store.get_data(run_id, lid)
                results[lid] = LayerResult(True, data, "cached")
                continue
            
            inputs = {}
            missing = []
            for dep in layer.depends_on:
                if self.run_store.has_data(run_id, dep):
                    inputs[dep] = self.run_store.get_data(run_id, dep)
                else:
                    missing.append(dep)
            
            if missing:
                results[lid] = LayerResult(False, None, f"missing deps: {missing}")
                continue
            
            doc = self.doc_store.get(run.doc_id)
            if doc:
                inputs["_doc"] = doc
            
            try:
                result = layer.process(inputs, self.context)
                if result.success:
                    self.run_store.set_data(run_id, lid, result.data)
                results[lid] = result
            except Exception as e:
                results[lid] = LayerResult(False, None, f"error: {e}")
        
        return results
    
    def get_dsl(self, run_id: str, layer_id: str) -> str | None:
        """Get layer data formatted as DSL."""
        layer = get_layer(layer_id)
        data = self.run_store.get_data(run_id, layer_id)
        if data is None:
            return None
        return layer.format_dsl(data)
