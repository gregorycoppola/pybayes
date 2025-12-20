# src/qbbn/core/layers/coref.py
"""
Coreference layer - link coreferent mentions.
"""

import json
from qbbn.core.layers import Layer, LayerResult, register_layer


COREF_PROMPT = """Identify coreference links in this sentence.

Coreference: two mentions that refer to the same entity.

For "If someone is a man then they are mortal":
- "someone" (index 1) and "they" (index 6) refer to the same person

Reply JSON:
{
  "coreferences": [
    {"index_a": 1, "index_b": 6}
  ]
}

Only include clear coreferences. Empty list if none.
"""


class CorefLayer(Layer):
    id = "coref"
    depends_on = ["correct", "clauses"]
    ext = ".coref"
    
    def process(self, inputs: dict, context: dict) -> LayerResult:
        correct_data = inputs.get("correct", [])
        tokens = [c["corrected"] for c in correct_data]
        
        openai = context.get("openai")
        if not openai:
            return LayerResult(False, None, "no openai client")
        
        prompt = "Tokens:\n" + "\n".join(f"{i}: {t}" for i, t in enumerate(tokens))
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": COREF_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        
        data = json.loads(response.choices[0].message.content)
        n_corefs = len(data.get("coreferences", []))
        
        return LayerResult(True, data, f"{n_corefs} coreferences")
    
    def parse_dsl(self, text: str) -> dict:
        """
        Parse:
        1 = 6
        3 = 8
        """
        coreferences = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            if "=" in line:
                a, b = line.split("=")
                coreferences.append({
                    "index_a": int(a.strip()),
                    "index_b": int(b.strip()),
                })
        
        return {"coreferences": coreferences}
    
    def format_dsl(self, data: dict) -> str:
        lines = []
        for c in data.get("coreferences", []):
            lines.append(f"{c['index_a']} = {c['index_b']}")
        return "\n".join(lines) if lines else "# no coreferences"


register_layer(CorefLayer())