"""
Logic layer - translate syntax to logical form, using KB links when available.
"""

from world.core.layers import Layer, LayerResult, register_layer


class LogicLayer(Layer):
    id = "logic"
    depends_on = ["base", "clauses", "args", "coref", "entities", "link"]
    ext = ".logic"
    
    def process(self, inputs: dict, context: dict) -> LayerResult:
        base_data = inputs.get("base", {})
        clauses_data = inputs.get("clauses", {})
        args_data = inputs.get("args", {})
        coref_data = inputs.get("coref", {})
        entities_data = inputs.get("entities", {})
        link_data = inputs.get("link", {})
        
        sentences = base_data.get("sentences", [])
        coreferences = coref_data.get("coreferences", [])
        
        # Build token lookup: (sent_idx, tok_idx) -> text
        token_lookup = {}
        for sent in sentences:
            for tok in sent["tokens"]:
                token_lookup[(sent["idx"], tok["idx"])] = tok["text"]
        
        # Build entity lookup from links
        # Prefer KB IDs when available, fall back to discourse IDs
        entity_lookup = {}
        
        for link in link_data.get("links", []):
            m = tuple(link["mention"])
            entity_lookup[m] = link["kb_id"]  # Use KB ID
        
        for ent in link_data.get("unlinked", []):
            m = tuple(ent["mention"])
            entity_lookup[m] = ent["discourse_id"]  # Use discourse ID
        
        # Build quantifier lookup: (sent_idx, tok_idx) -> var_name
        quant_lookup = {}
        var_map = {}
        for q in entities_data.get("quantifiers", []):
            m = tuple(q["mention"])
            quant_lookup[m] = q["var"]
            var_map[m] = q["var"]
        
        # Extend var_map with coreferences
        for coref in coreferences:
            a = tuple(coref["a"])
            b = tuple(coref["b"])
            if a in var_map:
                var_map[b] = var_map[a]
            elif b in var_map:
                var_map[a] = var_map[b]
        
        lines = []
        
        # Emit entity declarations for unlinked entities only
        # (KB entities are already declared in the KB)
        unlinked = link_data.get("unlinked", [])
        if unlinked:
            lines.append("# New entities (not in KB)")
            for ent in unlinked:
                lines.append(f"entity {ent['discourse_id']} : {ent.get('discourse_type', 'entity')}")
            lines.append("")
        
        # Note linked entities
        linked = link_data.get("links", [])
        if linked:
            lines.append("# Linked to KB")
            for link in linked:
                lines.append(f"# {link['discourse_id']} → {link['kb_id']}")
            lines.append("")
        
        # Collect quantifier variable types
        var_types = []
        for q in entities_data.get("quantifiers", []):
            var_types.append((q["var"], "entity"))
        
        # Process each sentence
        for args_sent in args_data.get("sentences", []):
            sent_idx = args_sent["sentence_idx"]
            
            # Find matching clauses sentence
            clauses_sent = None
            for cs in clauses_data.get("sentences", []):
                if cs["sentence_idx"] == sent_idx:
                    clauses_sent = cs
                    break
            
            if not clauses_sent:
                continue
            
            clauses = clauses_sent.get("clauses", [])
            
            # Check if this is a rule
            has_antecedent = any(c.get("label") == "antecedent" for c in clauses)
            has_consequent = any(c.get("label") == "consequent" for c in clauses)
            is_rule = var_types and has_antecedent and has_consequent
            
            if is_rule:
                lines.append(f"# Sentence {sent_idx}: Rule")
                
                antecedent_clause = None
                consequent_clause = None
                
                for clause_args in args_sent.get("clauses", []):
                    if clause_args.get("clause_label") == "antecedent":
                        antecedent_clause = clause_args
                    elif clause_args.get("clause_label") == "consequent":
                        consequent_clause = clause_args
                
                if antecedent_clause and consequent_clause:
                    premise = self._build_predicate(sent_idx, antecedent_clause, token_lookup, var_map, entity_lookup)
                    conclusion = self._build_predicate(sent_idx, consequent_clause, token_lookup, var_map, entity_lookup)
                    
                    vars_str = ", ".join(f"{v}:{t}" for v, t in var_types)
                    lines.append(f"rule [{vars_str}]: {premise} -> {conclusion}")
            else:
                lines.append(f"# Sentence {sent_idx}: Propositions")
                for clause_args in args_sent.get("clauses", []):
                    pred = self._build_predicate(sent_idx, clause_args, token_lookup, var_map, entity_lookup)
                    lines.append(pred)
            
            lines.append("")
        
        logic_text = "\n".join(lines)
        
        return LayerResult(True, {"text": logic_text}, "generated")
    
    def _build_predicate(self, sent_idx: int, clause_args: dict, token_lookup: dict, var_map: dict, entity_lookup: dict) -> str:
        """Build a predicate string from clause arguments."""
        verb_idx = clause_args["verb_index"]
        clause_start = clause_args["clause_start"]
        
        # Get verb
        verb = token_lookup.get((sent_idx, verb_idx), "?").lower()
        
        args = []
        for arg in clause_args.get("arguments", []):
            role = arg["role"]
            
            # Indices are relative to clause, convert to sentence
            abs_start = clause_start + arg["start"]
            abs_end = clause_start + arg["end"]
            
            # Check if any token is a variable or entity
            var_name = None
            entity_name = None
            for tok_idx in range(abs_start, abs_end):
                key = (sent_idx, tok_idx)
                if key in var_map:
                    var_name = var_map[key]
                    break
                if key in entity_lookup:
                    entity_name = entity_lookup[key]
                    break
            
            if var_name:
                args.append(f"{role}: {var_name}")
            elif entity_name:
                args.append(f"{role}: {entity_name}")
            else:
                # Use head word (last token, skip articles)
                head_idx = abs_end - 1
                head = token_lookup.get((sent_idx, head_idx), "?").lower()
                if head in {"a", "an", "the"} and abs_end - abs_start > 1:
                    head_idx = abs_end - 2
                    head = token_lookup.get((sent_idx, head_idx), "?").lower()
                args.append(f"{role}: {head}")
        
        return f"{verb}({', '.join(args)})"
    
    def parse_dsl(self, text: str) -> dict:
        return {"text": text}
    
    def format_dsl(self, data: dict) -> str:
        return data.get("text", "")


register_layer(LogicLayer())