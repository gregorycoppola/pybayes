"""
Coreference layer - link coreferent mentions across sentences.
"""

import json
from qbbn.core.layers import Layer, LayerResult, register_layer


COREF_PROMPT = """Identify coreference links in these sentences.

Coreference: two mentions that refer to the same entity.
Use (sentence_idx, token_idx) pairs.

For "If someone is a man then they are mortal":
- "someone" at (0, 1) and "they" at (0, 6) refer to same person

Reply JSON:
{
  "coreferences": [
    {"a": [0, 1], "b": [0, 6]}
  ]
}

Each entry has "a" and "b" as [sentence_idx, token_idx] pairs.
Empty list if no coreferences.
"""


class CorefLayer(Layer):
    id = "coref"
    depends_on = ["base"]
    ext = ".coref"
    
    def process(self, inputs: dict, context: dict) -> LayerResult:
        base_data = inputs.get("base", {})
        sentences = base_data.get("sentences", [])
        
        openai = context.get("openai")
        if not openai:
            return LayerResult(False, None, "no openai client")
        
        # Build prompt with all sentences
        prompt_lines = []
        for sent in sentences:
            prompt_lines.append(f"Sentence {sent['idx']}:")
            for tok in sent["tokens"]:
                prompt_lines.append(f"  ({sent['idx']}, {tok['idx']}): {tok['text']}")
        
        prompt = "\n".join(prompt_lines)
        
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
        (0, 1) = (0, 6)
        (0, 3) = (1, 0)
        """
        import re
        coreferences = []
        
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            match = re.match(r"\((\d+),\s*(\d+)\)\s*=\s*\((\d+),\s*(\d+)\)", line)
            if match:
                s1, t1, s2, t2 = match.groups()
                coreferences.append({
                    "a": [int(s1), int(t1)],
                    "b": [int(s2), int(t2)],
                })
        
        return {"coreferences": coreferences}
    
    def format_dsl(self, data: dict) -> str:
        lines = []
        for c in data.get("coreferences", []):
            a = c["a"]
            b = c["b"]
            lines.append(f"({a[0]}, {a[1]}) = ({b[0]}, {b[1]})")
        return "\n".join(lines) if lines else "# no coreferences"


register_layer(CorefLayer())