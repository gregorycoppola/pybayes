"""
Clauses layer - identify clause boundaries per sentence.
"""

import json
from world.core.layers import Layer, LayerResult, register_layer


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
    depends_on = ["base"]
    ext = ".clause"
    
    def process(self, inputs: dict, context: dict) -> LayerResult:
        base_data = inputs.get("base", {})
        sentences = base_data.get("sentences", [])
        
        openai = context.get("openai")
        if not openai:
            return LayerResult(False, None, "no openai client")
        
        result_sentences = []
        total_clauses = 0
        
        for sent in sentences:
            tokens = [t["text"] for t in sent["tokens"]]
            
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
            
            clause_data = json.loads(response.choices[0].message.content)
            
            result_sentences.append({
                "sentence_idx": sent["idx"],
                "clauses": clause_data.get("clauses", []),
                "skip_tokens": clause_data.get("skip_tokens", []),
            })
            
            total_clauses += len(clause_data.get("clauses", []))
        
        return LayerResult(True, {"sentences": result_sentences}, f"{total_clauses} clauses")
    
    def parse_dsl(self, text: str) -> dict:
        """
        Parse:
        # sentence 0
        [1:5] antecedent verb=2
        [6:9] consequent verb=7
        skip: 0 5
        """
        import re
        sentences = []
        current = None
        
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("# sentence"):
                if current is not None:
                    sentences.append(current)
                idx = int(line.split()[-1])
                current = {"sentence_idx": idx, "clauses": [], "skip_tokens": []}
            elif current is not None:
                if line.startswith("skip:"):
                    _, rest = line.split(":", 1)
                    current["skip_tokens"] = [int(x) for x in rest.strip().split()]
                elif line.startswith("["):
                    match = re.match(r"\[(\d+):(\d+)\]\s*(\w*)\s*verb=(\d+)", line)
                    if match:
                        start, end, label, verb = match.groups()
                        current["clauses"].append({
                            "start": int(start),
                            "end": int(end),
                            "label": label or "main",
                            "verb_index": int(verb),
                        })
        
        if current is not None:
            sentences.append(current)
        
        return {"sentences": sentences}
    
    def format_dsl(self, data: dict) -> str:
        lines = []
        for sent in data.get("sentences", []):
            lines.append(f"# sentence {sent['sentence_idx']}")
            for c in sent.get("clauses", []):
                lines.append(f"[{c['start']}:{c['end']}] {c.get('label', '')} verb={c['verb_index']}")
            skip = sent.get("skip_tokens", [])
            if skip:
                lines.append(f"skip: {' '.join(str(s) for s in skip)}")
            lines.append("")
        return "\n".join(lines)
    
    def validate(self, data: dict) -> list[str]:
        errors = []
        for sent in data.get("sentences", []):
            for c in sent.get("clauses", []):
                if c["start"] >= c["end"]:
                    errors.append(f"Sentence {sent['sentence_idx']}: invalid clause [{c['start']}:{c['end']}]")
                if c["verb_index"] < c["start"] or c["verb_index"] >= c["end"]:
                    errors.append(f"Sentence {sent['sentence_idx']}: verb {c['verb_index']} outside clause")
        return errors


register_layer(ClausesLayer())