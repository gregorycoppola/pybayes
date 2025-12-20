# src/qbbn/core/layers/clauses.py
"""
Clauses layer - identify clause boundaries.
"""

import json
from qbbn.core.layers import Layer, LayerResult, register_layer


CLAUSE_PROMPT = """Identify all clauses in this sentence.

CRITICAL: end index is EXCLUSIVE (Python slice style).
- To include token 8, end must be 9

For "If someone is a man then they are mortal" (tokens 0-8):
- Clause 1: start=1, end=5 → "someone is a man" (verb_index=2)
- Clause 2: start=6, end=9 → "they are mortal" (verb_index=7)
- skip_tokens: [0, 5] → "If", "then"

Reply JSON:
{
  "clauses": [
    {"start": 1, "end": 5, "verb_index": 2, "label": "antecedent"},
    {"start": 6, "end": 9, "verb_index": 7, "label": "consequent"}
  ],
  "skip_tokens": [0, 5]
}
"""


class ClausesLayer(Layer):
    id = "clauses"
    depends_on = ["correct"]
    ext = ".clause"
    
    def process(self, inputs: dict, context: dict) -> LayerResult:
        correct_data = inputs.get("correct", [])
        tokens = [c["corrected"] for c in correct_data]
        
        openai = context.get("openai")
        if not openai:
            return LayerResult(False, None, "no openai client")
        
        prompt = "Tokens:\n" + "\n".join(f"{i}: {t}" for i, t in enumerate(tokens))
        prompt += f"\n\nTotal: {len(tokens)} tokens"
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": CLAUSE_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        
        data = json.loads(response.choices[0].message.content)
        n_clauses = len(data.get("clauses", []))
        
        return LayerResult(True, data, f"{n_clauses} clauses")
    
    def parse_dsl(self, text: str) -> dict:
        """
        Parse:
        [1:5] antecedent verb=2
        [6:9] consequent verb=7
        skip: 0 5
        """
        clauses = []
        skip_tokens = []
        
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            if line.startswith("skip:"):
                _, rest = line.split(":", 1)
                skip_tokens = [int(x) for x in rest.strip().split()]
            elif line.startswith("["):
                import re
                match = re.match(r"\[(\d+):(\d+)\]\s*(\w*)\s*verb=(\d+)", line)
                if match:
                    start, end, label, verb = match.groups()
                    clauses.append({
                        "start": int(start),
                        "end": int(end),
                        "label": label or "main",
                        "verb_index": int(verb),
                    })
        
        return {"clauses": clauses, "skip_tokens": skip_tokens}
    
    def format_dsl(self, data: dict) -> str:
        lines = []
        for c in data.get("clauses", []):
            lines.append(f"[{c['start']}:{c['end']}] {c.get('label', '')} verb={c['verb_index']}")
        
        skip = data.get("skip_tokens", [])
        if skip:
            lines.append(f"skip: {' '.join(str(s) for s in skip)}")
        
        return "\n".join(lines)
    
    def validate(self, data: dict) -> list[str]:
        errors = []
        for c in data.get("clauses", []):
            if c["start"] >= c["end"]:
                errors.append(f"Invalid clause bounds: [{c['start']}:{c['end']}]")
            if c["verb_index"] < c["start"] or c["verb_index"] >= c["end"]:
                errors.append(f"Verb {c['verb_index']} not in clause [{c['start']}:{c['end']}]")
        return errors


register_layer(ClausesLayer())