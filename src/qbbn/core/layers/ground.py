"""
Ground layer - expand rules with entity bindings using KB.
"""

from qbbn.core.layers import Layer, LayerResult, register_layer


class GroundLayer(Layer):
    id = "ground"
    depends_on = ["logic", "link"]
    ext = ".ground"
    
    def process(self, inputs: dict, context: dict) -> LayerResult:
        logic_data = inputs.get("logic", {})
        link_data = inputs.get("link", {})
        logic_text = logic_data.get("text", "")
        
        kb = context.get("kb")
        if not kb:
            return LayerResult(False, None, "no KB in context")
        
        if not logic_text:
            return LayerResult(False, None, "no logic text")
        
        try:
            # Build combined logic text with KB entities
            combined_lines = []
            
            # Add entity declarations from KB
            combined_lines.append("# KB Entities")
            for ent in kb.entities.values():
                combined_lines.append(f"entity {ent.id} : {ent.type}")
            combined_lines.append("")
            
            # Add KB facts
            if kb.facts:
                combined_lines.append("# KB Facts")
                for fact in kb.facts:
                    args_str = ", ".join(f"{k}: {v}" for k, v in fact.args.items())
                    combined_lines.append(f"{fact.predicate}({args_str})")
                combined_lines.append("")
            
            # Add KB rules
            if kb.rules:
                combined_lines.append("# KB Rules")
                for rule in kb.rules:
                    vars_str = ", ".join(f"{v}:{t}" for v, t in rule.variables)
                    prem_args = ", ".join(f"{k}: {v}" for k, v in rule.premise[1].items())
                    conc_args = ", ".join(f"{k}: {v}" for k, v in rule.conclusion[1].items())
                    line = f"rule [{vars_str}]: {rule.premise[0]}({prem_args}) -> {rule.conclusion[0]}({conc_args})"
                    if rule.weight != 1.0:
                        line += f" [{rule.weight}]"
                    combined_lines.append(line)
                combined_lines.append("")
            
            # Add document propositions (skip comments and entity decls from logic output)
            combined_lines.append("# Document Propositions")
            for line in logic_text.split("\n"):
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("entity"):
                    continue
                if line.startswith("rule"):
                    continue  # Skip doc rules for now, use KB rules
                combined_lines.append(line)
            
            combined_text = "\n".join(combined_lines)
            
            # Now parse and ground
            from qbbn.core.logical_lang import parse_logical
            from qbbn.core.horn import KnowledgeBase as HornKB, format_horn_clause
            
            doc = parse_logical(combined_text)
            horn_kb = HornKB.from_logical_document(doc)
            grounded = horn_kb.ground_all()
            
            lines = []
            for clause in grounded:
                lines.append(format_horn_clause(clause, show_vars=False))
            
            return LayerResult(True, {
                "clauses": [c.to_dict() for c in grounded],
                "text": "\n".join(lines),
                "combined_logic": combined_text,
            }, f"{len(grounded)} grounded clauses")
        
        except Exception as e:
            return LayerResult(False, None, f"ground error: {e}")
    
    def parse_dsl(self, text: str) -> dict:
        return {"text": text}
    
    def format_dsl(self, data: dict) -> str:
        return data.get("text", "")


register_layer(GroundLayer())