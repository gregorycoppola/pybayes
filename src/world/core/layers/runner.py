"""
Layer execution runner - works on runs with KB from store.
"""

from world.core.layers import get_layer, resolve_dependencies, LayerResult


class LayerRunner:
    """Runs layers on a run workspace."""
    
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