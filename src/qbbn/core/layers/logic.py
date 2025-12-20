# src/qbbn/core/layers/logic.py
"""
Logic layer - translate syntax to logical form.
"""

from qbbn.core.layers import Layer, LayerResult, register_layer


class LogicLayer(Layer):
    id = "logic"
    depends_on = ["correct", "clauses", "args", "coref"]
    ext = ".logic"
    
    def process(self, inputs: dict, context: dict) -> LayerResult:
        correct_data = inputs.get("correct", [])
        tokens = [c["corrected"] for c in correct_data]
        
        clauses_data = inputs.get("clauses", {})
        args_data = inputs.get("args", [])
        coref_data = inputs.get("coref", {})
        
        clauses = clauses_data.get("clauses", [])
        coreferences = coref_data.get("coreferences", [])
        
        lines = []
        
        # Build coref map: token_index -> var_name
        var_map = {}
        var_types = []
        for i, coref in enumerate(coreferences):
            var_name = f"x{i}"
            var_map[coref["index_a"]] = var_name
            var_map[coref["index_b"]] = var_name
            var_types.append((var_name, "entity"))
        
        # Collect entities (non-variable heads)
        entities = set()
        for clause_args in args_data:
            for arg in clause_args.get("arguments", []):
                head_idx = clause_args["clause_start"] + arg["end"] - 1
                if head_idx not in var_map:
                    head_word = tokens[head_idx].lower()
                    # Skip articles and simple words
                    if head_word not in {"a", "an", "the"}:
                        entities.add(head_word)
        
        # Determine if this is a rule or proposition
        has_coref = len(coreferences) > 0
        has_antecedent = any(c.get("label") == "antecedent" for c in clauses)
        has_consequent = any(c.get("label") == "consequent" for c in clauses)
        is_rule = has_coref and has_antecedent and has_consequent
        
        if is_rule:
            # Output as rule
            lines.append("# Rule (generated from syntax)")
            lines.append("")
            
            # Find antecedent and consequent
            antecedent_args = None
            consequent_args = None
            
            for clause_args in args_data:
                if clause_args.get("clause_label") == "antecedent":
                    antecedent_args = clause_args
                elif clause_args.get("clause_label") == "consequent":
                    consequent_args = clause_args
            
            if antecedent_args and consequent_args:
                premise = self._build_predicate(antecedent_args, tokens, var_map)
                conclusion = self._build_predicate(consequent_args, tokens, var_map)
                
                vars_str = ", ".join(f"{v}:{t}" for v, t in var_types)
                lines.append(f"rule [{vars_str}]: {premise} -> {conclusion}")
        else:
            # Output as propositions
            if entities:
                lines.append("# Entities")
                for e in sorted(entities):
                    lines.append(f"entity {e} : entity")
                lines.append("")
            
            lines.append("# Propositions")
            for clause_args in args_data:
                pred = self._build_predicate(clause_args, tokens, var_map)
                lines.append(pred)
        
        logic_text = "\n".join(lines)
        
        return LayerResult(True, {"text": logic_text}, "generated")
    
    def _build_predicate(self, clause_args: dict, tokens: list[str], var_map: dict[int, str]) -> str:
        """Build a predicate string from clause arguments."""
        verb_idx = clause_args["verb_index"]
        clause_start = clause_args["clause_start"]
        
        # Get verb (relative to full token list)
        verb = tokens[verb_idx].lower()
        
        args = []
        for arg in clause_args.get("arguments", []):
            role = arg["role"]
            
            # Absolute indices
            abs_start = clause_start + arg["start"]
            abs_end = clause_start + arg["end"]
            
            # Check if any token is a variable
            var_name = None
            for idx in range(abs_start, abs_end):
                if idx in var_map:
                    var_name = var_map[idx]
                    break
            
            if var_name:
                args.append(f"{role}: {var_name}")
            else:
                # Use head word (last token, skip articles)
                head_idx = abs_end - 1
                head = tokens[head_idx].lower()
                if head in {"a", "an", "the"} and abs_end - abs_start > 1:
                    head_idx = abs_end - 2
                    head = tokens[head_idx].lower()
                args.append(f"{role}: {head}")
        
        return f"{verb}({', '.join(args)})"
    
    def parse_dsl(self, text: str) -> dict:
        """Just store the raw text."""
        return {"text": text}
    
    def format_dsl(self, data: dict) -> str:
        return data.get("text", "")


register_layer(LogicLayer())