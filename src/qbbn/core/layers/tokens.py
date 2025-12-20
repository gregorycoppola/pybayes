# src/qbbn/core/layers/tokens.py
"""
Tokens layer - basic tokenization.
"""

from qbbn.core.layers import Layer, LayerResult, register_layer


class TokensLayer(Layer):
    id = "tokens"
    depends_on = []
    ext = ".tok"
    
    def process(self, inputs: dict, context: dict) -> LayerResult:
        from qbbn.core.tokenize import tokenize
        
        doc = inputs.get("_doc")
        if not doc:
            return LayerResult(False, None, "no document")
        
        tokens = tokenize(doc.text)
        data = [{"text": t.text, "position": t.position} for t in tokens]
        
        return LayerResult(True, data, f"{len(data)} tokens")
    
    def parse_dsl(self, text: str) -> list[dict]:
        """
        Parse: 0:If 3:someone 11:is ...
        """
        tokens = []
        for part in text.strip().split():
            if ":" in part:
                pos, txt = part.split(":", 1)
                tokens.append({"position": int(pos), "text": txt})
        return tokens
    
    def format_dsl(self, data: list[dict]) -> str:
        return " ".join(f"{t['position']}:{t['text']}" for t in data)


register_layer(TokensLayer())