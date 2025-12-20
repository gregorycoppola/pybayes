"""
Link layer - connects discourse entities to knowledge base entities.
"""

from qbbn.core.layers import Layer, LayerResult, register_layer
from qbbn.core.kb import load_kb


class LinkLayer(Layer):
    id = "link"
    depends_on = ["entities"]
    ext = ".link"
    
    def process(self, inputs: dict, context: dict) -> LayerResult:
        entities_data = inputs.get("entities", {})
        
        # Load KB from context or default location
        kb_dir = context.get("kb_dir", "kb")
        kb = load_kb(kb_dir)
        
        discourse_entities = entities_data.get("entities", [])
        
        links = []
        unlinked = []
        
        for ent in discourse_entities:
            ent_id = ent["id"]
            
            # Try to find in KB
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
            "kb_entities_count": len(kb.entities),
            "kb_facts_count": len(kb.facts),
            "kb_rules_count": len(kb.rules),
        }
        
        n_linked = len(links)
        n_unlinked = len(unlinked)
        
        return LayerResult(True, data, f"{n_linked} linked, {n_unlinked} new")
    
    def parse_dsl(self, text: str) -> dict:
        """
        Parse:
        # linked
        socrates → kb:socrates @ (0, 0)
        
        # unlinked
        stranger : person @ (1, 3) [new]
        """
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
                # socrates → kb:socrates @ (0, 0)
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
                # stranger : person @ (1, 3) [new]
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
        
        kb_info = []
        if "kb_entities_count" in data:
            kb_info.append(f"# KB: {data['kb_entities_count']} entities, {data.get('kb_facts_count', 0)} facts, {data.get('kb_rules_count', 0)} rules")
        
        if kb_info:
            lines.extend(kb_info)
        
        return "\n".join(lines) if lines else "# no entities to link"


register_layer(LinkLayer())