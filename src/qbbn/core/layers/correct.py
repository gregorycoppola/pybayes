# src/qbbn/core/layers/correct.py
"""
Correct layer - spelling correction.
"""

from qbbn.core.layers import Layer, LayerResult, register_layer


class CorrectLayer(Layer):
    id = "correct"
    depends_on = ["tokens"]
    ext = ".cor"
    
    def process(self, inputs: dict, context: dict) -> LayerResult:
        from qbbn.core.tokenize import Token, SpellCorrector
        
        tokens_data = inputs.get("tokens", [])
        tokens = [Token(t["text"], t["position"]) for t in tokens_data]
        
        openai = context.get("openai")
        corrector = SpellCorrector(openai)
        corrected = corrector.correct(tokens)
        
        data = [{"original": c.original, "corrected": c.corrected, "position": c.position} 
                for c in corrected]
        
        changes = sum(1 for c in corrected if c.original != c.corrected)
        return LayerResult(True, data, f"{changes} corrections")
    
    def parse_dsl(self, text: str) -> list[dict]:
        """
        Parse:
        0: If -> If
        3: somone -> someone
        """
        data = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            if ":" in line and "->" in line:
                pos_part, rest = line.split(":", 1)
                orig, corr = rest.split("->")
                data.append({
                    "position": int(pos_part.strip()),
                    "original": orig.strip(),
                    "corrected": corr.strip(),
                })
        return data
    
    def format_dsl(self, data: list[dict]) -> str:
        lines = []
        for d in data:
            if d["original"] != d["corrected"]:
                lines.append(f"{d['position']}: {d['original']} -> {d['corrected']}")
            else:
                lines.append(f"{d['position']}: {d['corrected']}")
        return "\n".join(lines)


register_layer(CorrectLayer())