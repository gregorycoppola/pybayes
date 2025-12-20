"""
Link layer - connects discourse entities to knowledge base entities.
"""

from world.core.layers import Layer, LayerResult, register_layer


class LinkLayer(Layer):
    id = "link"
    depends_on = ["entities"]
    ext = ".link"
    
    def process(self, inputs: dict, context: dict) -> LayerResult:
        entities_data = inputs.get("entities", {})
        
        # Get KB from context
        kb = context.get("kb")
        if not kb:
            return LayerResult(False, None, "no KB in context")
        
        discourse_entities = entities_data.get("entities", [])
        
        links = []
        unlinked = []
        
        for ent in discourse_entities:
            ent_id = ent["id"]
            
            kb_entity = kb.get_entity(ent_id)
            
            if kb_entity:
                links.append({
                    "discourse_id": ent_id,
                    "discourse_type": ent["type"],
                    "mention": ent["mention"],
                    "kb_id": kb_entity.id,
                    "kb_type": kb_entity.type,
                    "status": "linked",
                })
            else:
                unlinked.append({
                    "discourse_id": ent_id,
                    "discourse_type": ent["type"],
                    "mention": ent["mention"],
                    "kb_id": None,
                    "kb_type": None,
                    "status": "new",
                })
        
        data = {
            "links": links,
            "unlinked": unlinked,
            "kb_entity_count": len(kb.entities),
            "kb_fact_count": len(kb.facts),
            "kb_rule_count": len(kb.rules),
        }
        
        return LayerResult(True, data, f"{len(links)} linked, {len(unlinked)} new")
    
    def parse_dsl(self, text: str) -> dict:
        import re
        links = []
        unlinked = []
        
        section = None
        
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            
            if line == "# linked":
                section = "linked"
            elif line == "# unlinked":
                section = "unlinked"
            elif section == "linked":
                match = re.match(r"(\w+)\s*[→->]+\s*kb:(\w+)\s*@\s*\((\d+),\s*(\d+)\)", line)
                if match:
                    disc_id, kb_id, s, t = match.groups()
                    links.append({
                        "discourse_id": disc_id,
                        "kb_id": kb_id,
                        "mention": [int(s), int(t)],
                        "status": "linked",
                    })
            elif section == "unlinked":
                match = re.match(r"(\w+)\s*:\s*(\w+)\s*@\s*\((\d+),\s*(\d+)\)", line)
                if match:
                    disc_id, disc_type, s, t = match.groups()
                    unlinked.append({
                        "discourse_id": disc_id,
                        "discourse_type": disc_type,
                        "mention": [int(s), int(t)],
                        "status": "new",
                    })
        
        return {"links": links, "unlinked": unlinked}
    
    def format_dsl(self, data: dict) -> str:
        lines = []
        
        links = data.get("links", [])
        if links:
            lines.append("# linked")
            for link in links:
                m = link["mention"]
                lines.append(f"{link['discourse_id']} → kb:{link['kb_id']} @ ({m[0]}, {m[1]})")
            lines.append("")
        
        unlinked = data.get("unlinked", [])
        if unlinked:
            lines.append("# unlinked")
            for ent in unlinked:
                m = ent["mention"]
                lines.append(f"{ent['discourse_id']} : {ent.get('discourse_type', '?')} @ ({m[0]}, {m[1]}) [new]")
            lines.append("")
        
        return "\n".join(lines) if lines else "# no entities to link"


register_layer(LinkLayer())