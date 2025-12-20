"""
Ground layer - expand rules with entity bindings.
"""

from qbbn.core.layers import Layer, LayerResult, register_layer


class GroundLayer(Layer):
    id = "ground"
    depends_on = ["logic"]
    ext = ".ground"
    
    def process(self, inputs: dict, context: dict) -> LayerResult:
        logic_data = inputs.get("logic", {})
        logic_text = logic_data.get("text", "")
        
        if not logic_text:
            return LayerResult(False, None, "no logic text")
        
        try:
            from qbbn.core.logical_lang import parse_logical
            from qbbn.core.horn import KnowledgeBase, format_horn_clause
            
            doc = parse_logical(logic_text)
            kb = KnowledgeBase.from_logical_document(doc)
            grounded = kb.ground_all()
            
            lines = []
            for clause in grounded:
                lines.append(format_horn_clause(clause, show_vars=False))
            
            return LayerResult(True, {
                "clauses": [c.to_dict() for c in grounded],
                "text": "\n".join(lines),
            }, f"{len(grounded)} grounded clauses")
        
        except Exception as e:
            return LayerResult(False, None, f"parse error: {e}")
    
    def parse_dsl(self, text: str) -> dict:
        return {"text": text}
    
    def format_dsl(self, data: dict) -> str:
        return data.get("text", "")


register_layer(GroundLayer())