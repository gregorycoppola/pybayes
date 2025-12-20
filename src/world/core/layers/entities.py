"""
Entities layer - identify named entities, types, and quantifiers.
"""

import json
from world.core.layers import Layer, LayerResult, register_layer


ENTITIES_PROMPT = """Identify entities, types, and quantifiers in these sentences.

ENTITIES: Named/specific things (proper nouns, definite references)
- "Socrates" → entity, type person
- "the bank" → entity, type place
- "my car" → entity, type object

TYPES: Categories/kinds (common nouns used as types in predicates)
- "man", "mortal", "philosopher" → types

QUANTIFIERS: Words that introduce variables
- "someone", "everyone", "anyone" → quantifier, introduce variable
- "they", "it" when referring to quantified entity → NOT new quantifier, just coreference

Reply JSON:
{
  "entities": [
    {"id": "socrates", "type": "person", "mention": [0, 0]}
  ],
  "types": [
    {"id": "man", "mention": [0, 4]},
    {"id": "mortal", "mention": [0, 8]}
  ],
  "quantifiers": [
    {"token": "someone", "var": "x0", "mention": [0, 1]}
  ]
}

mention is [sentence_idx, token_idx].
Use lowercase for ids.
Variable names: x0, x1, x2...
"""


class EntitiesLayer(Layer):
    id = "entities"
    depends_on = ["base"]
    ext = ".ent"
    
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
                {"role": "system", "content": ENTITIES_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        
        data = json.loads(response.choices[0].message.content)
        
        n_ent = len(data.get("entities", []))
        n_types = len(data.get("types", []))
        n_quant = len(data.get("quantifiers", []))
        
        return LayerResult(True, data, f"{n_ent} entities, {n_types} types, {n_quant} quantifiers")
    
    def parse_dsl(self, text: str) -> dict:
        """
        Parse:
        # entities
        socrates : person @ (0, 0)
        
        # types
        man @ (0, 4)
        mortal @ (0, 8)
        
        # quantifiers
        someone → x0 @ (0, 1)
        """
        import re
        
        entities = []
        types = []
        quantifiers = []
        
        section = None
        
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            
            if line == "# entities":
                section = "entities"
            elif line == "# types":
                section = "types"
            elif line == "# quantifiers":
                section = "quantifiers"
            elif section == "entities":
                # socrates : person @ (0, 0)
                match = re.match(r"(\w+)\s*:\s*(\w+)\s*@\s*\((\d+),\s*(\d+)\)", line)
                if match:
                    id_, type_, s, t = match.groups()
                    entities.append({
                        "id": id_,
                        "type": type_,
                        "mention": [int(s), int(t)],
                    })
            elif section == "types":
                # man @ (0, 4)
                match = re.match(r"(\w+)\s*@\s*\((\d+),\s*(\d+)\)", line)
                if match:
                    id_, s, t = match.groups()
                    types.append({
                        "id": id_,
                        "mention": [int(s), int(t)],
                    })
            elif section == "quantifiers":
                # someone → x0 @ (0, 1)
                match = re.match(r"(\w+)\s*[→->]+\s*(\w+)\s*@\s*\((\d+),\s*(\d+)\)", line)
                if match:
                    token, var, s, t = match.groups()
                    quantifiers.append({
                        "token": token,
                        "var": var,
                        "mention": [int(s), int(t)],
                    })
        
        return {
            "entities": entities,
            "types": types,
            "quantifiers": quantifiers,
        }
    
    def format_dsl(self, data: dict) -> str:
        lines = []
        
        entities = data.get("entities", [])
        if entities:
            lines.append("# entities")
            for e in entities:
                m = e["mention"]
                lines.append(f"{e['id']} : {e['type']} @ ({m[0]}, {m[1]})")
            lines.append("")
        
        types = data.get("types", [])
        if types:
            lines.append("# types")
            for t in types:
                m = t["mention"]
                lines.append(f"{t['id']} @ ({m[0]}, {m[1]})")
            lines.append("")
        
        quantifiers = data.get("quantifiers", [])
        if quantifiers:
            lines.append("# quantifiers")
            for q in quantifiers:
                m = q["mention"]
                lines.append(f"{q['token']} → {q['var']} @ ({m[0]}, {m[1]})")
            lines.append("")
        
        return "\n".join(lines) if lines else "# no entities"


register_layer(EntitiesLayer())