"""
Arguments layer - identify verb arguments per clause per sentence.
"""

import json
from world.core.layers import Layer, LayerResult, register_layer


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
    depends_on = ["base", "clauses"]
    ext = ".args"
    
    def process(self, inputs: dict, context: dict) -> LayerResult:
        base_data = inputs.get("base", {})
        clauses_data = inputs.get("clauses", {})
        
        sentences = base_data.get("sentences", [])
        clause_sentences = clauses_data.get("sentences", [])
        
        openai = context.get("openai")
        if not openai:
            return LayerResult(False, None, "no openai client")
        
        # Build lookup
        sent_tokens = {s["idx"]: [t["text"] for t in s["tokens"]] for s in sentences}
        
        result_sentences = []
        total_args = 0
        
        for clause_sent in clause_sentences:
            sent_idx = clause_sent["sentence_idx"]
            tokens = sent_tokens.get(sent_idx, [])
            
            clause_results = []
            
            for clause in clause_sent.get("clauses", []):
                clause_tokens = tokens[clause["start"]:clause["end"]]
                verb_rel = clause["verb_index"] - clause["start"]
                
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
                
                clause_results.append({
                    "clause_start": clause["start"],
                    "clause_end": clause["end"],
                    "clause_label": clause.get("label", ""),
                    "verb_index": clause["verb_index"],
                    "arguments": args.get("arguments", []),
                })
                
                total_args += len(args.get("arguments", []))
            
            result_sentences.append({
                "sentence_idx": sent_idx,
                "clauses": clause_results,
            })
        
        return LayerResult(True, {"sentences": result_sentences}, f"{total_args} arguments")
    
    def parse_dsl(self, text: str) -> dict:
        """
        Parse:
        # sentence 0
        clause [1:5] antecedent verb=2
          agent [0:1]
          theme [2:4]
        """
        import re
        sentences = []
        current_sent = None
        current_clause = None
        
        for line in text.strip().split("\n"):
            orig_line = line
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("# sentence"):
                if current_clause is not None and current_sent is not None:
                    current_sent["clauses"].append(current_clause)
                if current_sent is not None:
                    sentences.append(current_sent)
                idx = int(line.split()[-1])
                current_sent = {"sentence_idx": idx, "clauses": []}
                current_clause = None
            elif line.startswith("clause"):
                if current_clause is not None and current_sent is not None:
                    current_sent["clauses"].append(current_clause)
                match = re.match(r"clause\s+\[(\d+):(\d+)\]\s*(\w*)\s*verb=(\d+)", line)
                if match:
                    start, end, label, verb = match.groups()
                    current_clause = {
                        "clause_start": int(start),
                        "clause_end": int(end),
                        "clause_label": label,
                        "verb_index": int(verb),
                        "arguments": [],
                    }
            elif orig_line.startswith("  ") and current_clause is not None:
                match = re.match(r"(\w+)\s+\[(\d+):(\d+)\]", line)
                if match:
                    role, start, end = match.groups()
                    current_clause["arguments"].append({
                        "role": role,
                        "start": int(start),
                        "end": int(end),
                    })
        
        if current_clause is not None and current_sent is not None:
            current_sent["clauses"].append(current_clause)
        if current_sent is not None:
            sentences.append(current_sent)
        
        return {"sentences": sentences}
    
    def format_dsl(self, data: dict) -> str:
        lines = []
        for sent in data.get("sentences", []):
            lines.append(f"# sentence {sent['sentence_idx']}")
            for c in sent.get("clauses", []):
                lines.append(f"clause [{c['clause_start']}:{c['clause_end']}] {c['clause_label']} verb={c['verb_index']}")
                for arg in c.get("arguments", []):
                    lines.append(f"  {arg['role']} [{arg['start']}:{arg['end']}]")
            lines.append("")
        return "\n".join(lines)


register_layer(ArgsLayer())