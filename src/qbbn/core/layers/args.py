# src/qbbn/core/layers/args.py
"""
Arguments layer - identify verb arguments within clauses.
"""

import json
from qbbn.core.layers import Layer, LayerResult, register_layer


ARG_PROMPT = """Identify arguments of the verb.

CRITICAL: end index is EXCLUSIVE (Python slice style).
- To include token at index 4, end must be 5

For clause "they are mortal" with verb "are" at index 1:
- agent: start=0, end=1 → "they"  
- theme: start=2, end=3 → "mortal"

Reply JSON:
{
  "arguments": [
    {"start": 0, "end": 1, "role": "agent"},
    {"start": 2, "end": 3, "role": "theme"}
  ]
}

Roles: agent, patient, theme, goal, source, location, instrument, time
"""


class ArgsLayer(Layer):
    id = "args"
    depends_on = ["correct", "clauses"]
    ext = ".args"
    
    def process(self, inputs: dict, context: dict) -> LayerResult:
        correct_data = inputs.get("correct", [])
        tokens = [c["corrected"] for c in correct_data]
        
        clause_data = inputs.get("clauses", {})
        clauses = clause_data.get("clauses", [])
        
        openai = context.get("openai")
        if not openai:
            return LayerResult(False, None, "no openai client")
        
        results = []
        for c in clauses:
            clause_tokens = tokens[c["start"]:c["end"]]
            verb_rel = c["verb_index"] - c["start"]
            
            prompt = "Clause tokens:\n" + "\n".join(f"{i}: {t}" for i, t in enumerate(clause_tokens))
            prompt += f"\n\nVerb: {clause_tokens[verb_rel]} (index {verb_rel})"
            prompt += f"\nTotal: {len(clause_tokens)} tokens"
            
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": ARG_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            
            args = json.loads(response.choices[0].message.content)
            results.append({
                "clause_start": c["start"],
                "clause_end": c["end"],
                "clause_label": c.get("label", ""),
                "verb_index": c["verb_index"],
                "arguments": args.get("arguments", []),
            })
        
        return LayerResult(True, results, f"{len(results)} clauses analyzed")
    
    def parse_dsl(self, text: str) -> list[dict]:
        """
        Parse:
        clause [1:5] antecedent verb=2:
          agent [1:2]
          theme [3:5]
        """
        import re
        results = []
        current = None
        
        for line in text.strip().split("\n"):
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue
            
            if line.startswith("clause"):
                if current:
                    results.append(current)
                
                match = re.match(r"clause\s+\[(\d+):(\d+)\]\s*(\w*)\s*verb=(\d+)", line)
                if match:
                    start, end, label, verb = match.groups()
                    current = {
                        "clause_start": int(start),
                        "clause_end": int(end),
                        "clause_label": label,
                        "verb_index": int(verb),
                        "arguments": [],
                    }
            elif current and line.startswith("  "):
                match = re.match(r"\s+(\w+)\s+\[(\d+):(\d+)\]", line)
                if match:
                    role, start, end = match.groups()
                    current["arguments"].append({
                        "role": role,
                        "start": int(start),
                        "end": int(end),
                    })
        
        if current:
            results.append(current)
        
        return results
    
    def format_dsl(self, data: list[dict]) -> str:
        lines = []
        for c in data:
            lines.append(f"clause [{c['clause_start']}:{c['clause_end']}] {c['clause_label']} verb={c['verb_index']}:")
            for arg in c.get("arguments", []):
                lines.append(f"  {arg['role']} [{arg['start']}:{arg['end']}]")
        return "\n".join(lines)


register_layer(ArgsLayer())