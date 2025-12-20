"""
Knowledge Base - stored with UUID, loaded from .logic DSL.
"""

import json
import uuid
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class KBEntity:
    id: str
    type: str
    aliases: list[str] = field(default_factory=list)


@dataclass
class KBFact:
    predicate: str
    args: dict[str, str]


@dataclass
class KBRule:
    variables: list[tuple[str, str]]
    premise: tuple[str, dict[str, str]]
    conclusion: tuple[str, dict[str, str]]
    weight: float = 1.0


@dataclass 
class KnowledgeBase:
    id: str
    name: str
    created_at: str
    entities: dict[str, KBEntity] = field(default_factory=dict)
    facts: list[KBFact] = field(default_factory=list)
    rules: list[KBRule] = field(default_factory=list)
    
    def get_entity(self, id_or_alias: str) -> KBEntity | None:
        id_lower = id_or_alias.lower()
        
        if id_lower in self.entities:
            return self.entities[id_lower]
        
        for ent in self.entities.values():
            if id_lower in [a.lower() for a in ent.aliases]:
                return ent
        
        return None
    
    def get_entities_by_type(self, type_name: str) -> list[KBEntity]:
        return [e for e in self.entities.values() if e.type == type_name]
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "entities": {
                eid: {"id": e.id, "type": e.type, "aliases": e.aliases}
                for eid, e in self.entities.items()
            },
            "facts": [
                {"predicate": f.predicate, "args": f.args}
                for f in self.facts
            ],
            "rules": [
                {
                    "variables": r.variables,
                    "premise": {"predicate": r.premise[0], "args": r.premise[1]},
                    "conclusion": {"predicate": r.conclusion[0], "args": r.conclusion[1]},
                    "weight": r.weight,
                }
                for r in self.rules
            ],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeBase":
        kb = cls(
            id=data["id"],
            name=data["name"],
            created_at=data["created_at"],
        )
        
        for eid, edata in data.get("entities", {}).items():
            kb.entities[eid] = KBEntity(
                id=edata["id"],
                type=edata["type"],
                aliases=edata.get("aliases", []),
            )
        
        for fdata in data.get("facts", []):
            kb.facts.append(KBFact(
                predicate=fdata["predicate"],
                args=fdata["args"],
            ))
        
        for rdata in data.get("rules", []):
            kb.rules.append(KBRule(
                variables=rdata["variables"],
                premise=(rdata["premise"]["predicate"], rdata["premise"]["args"]),
                conclusion=(rdata["conclusion"]["predicate"], rdata["conclusion"]["args"]),
                weight=rdata.get("weight", 1.0),
            ))
        
        return kb
    
    def to_dsl(self) -> str:
        """Export as .logic DSL."""
        lines = []
        
        if self.entities:
            lines.append("# Entities")
            for ent in self.entities.values():
                lines.append(f"entity {ent.id} : {ent.type}")
            lines.append("")
        
        if self.facts:
            lines.append("# Facts")
            for fact in self.facts:
                args_str = ", ".join(f"{k}: {v}" for k, v in fact.args.items())
                lines.append(f"{fact.predicate}({args_str})")
            lines.append("")
        
        if self.rules:
            lines.append("# Rules")
            for rule in self.rules:
                vars_str = ", ".join(f"{v}:{t}" for v, t in rule.variables)
                prem_args = ", ".join(f"{k}: {v}" for k, v in rule.premise[1].items())
                conc_args = ", ".join(f"{k}: {v}" for k, v in rule.conclusion[1].items())
                line = f"rule [{vars_str}]: {rule.premise[0]}({prem_args}) -> {rule.conclusion[0]}({conc_args})"
                if rule.weight != 1.0:
                    line += f" [{rule.weight}]"
                lines.append(line)
            lines.append("")
        
        return "\n".join(lines)


class KBStore:
    """Stores knowledge bases in Redis."""
    
    def __init__(self, client):
        self.client = client
    
    def _kb_key(self, kb_id: str) -> str:
        return f"qbbn:kb:{kb_id}"
    
    def _kb_list_key(self) -> str:
        return "qbbn:kbs"
    
    def create(self, name: str, dsl_text: str) -> str:
        """Create KB from DSL text, returns kb_id."""
        kb_id = uuid.uuid4().hex[:12]
        
        kb = KnowledgeBase(
            id=kb_id,
            name=name,
            created_at=datetime.utcnow().isoformat(),
        )
        
        # Parse DSL
        _parse_dsl_into_kb(kb, dsl_text)
        
        # Store
        self.client.set(self._kb_key(kb_id), json.dumps(kb.to_dict()))
        self.client.rpush(self._kb_list_key(), kb_id)
        
        return kb_id
    
    def get(self, kb_id: str) -> KnowledgeBase | None:
        data = self.client.get(self._kb_key(kb_id))
        if not data:
            return None
        return KnowledgeBase.from_dict(json.loads(data))
    
    def list_all(self) -> list[KnowledgeBase]:
        kb_ids = self.client.lrange(self._kb_list_key(), 0, -1)
        kbs = []
        for kid in kb_ids:
            kb = self.get(kid.decode())
            if kb:
                kbs.append(kb)
        return kbs
    
    def delete(self, kb_id: str):
        self.client.delete(self._kb_key(kb_id))
        self.client.lrem(self._kb_list_key(), 0, kb_id)


def _parse_dsl_into_kb(kb: KnowledgeBase, text: str):
    """Parse .logic DSL and populate KB."""
    from qbbn.core.logical_lang import parse_logical
    
    try:
        doc = parse_logical(text)
    except Exception as e:
        raise ValueError(f"Failed to parse DSL: {e}")
    
    # Debug: print what we get
    # print(f"DEBUG doc.entities: {doc.entities}")
    # print(f"DEBUG doc.predicates: {doc.predicates}")
    # print(f"DEBUG doc.rules: {doc.rules}")
    
    for ent in doc.entities:
        # Handle both object and tuple forms
        if hasattr(ent, 'name'):
            name = ent.name
            type_name = ent.type_name
        else:
            # Assume it's a tuple or has different structure
            name = str(ent[0]) if isinstance(ent, (list, tuple)) else str(ent)
            type_name = str(ent[1]) if isinstance(ent, (list, tuple)) and len(ent) > 1 else "entity"
        
        kb.entities[name.lower()] = KBEntity(
            id=name.lower(),
            type=type_name,
            aliases=[name],
        )
    
    for pred in doc.predicates:
        args = {}
        if hasattr(pred, 'arguments'):
            for arg in pred.arguments:
                if hasattr(arg, 'role'):
                    args[arg.role] = arg.value.lower() if hasattr(arg, 'value') else str(arg.value)
        elif hasattr(pred, 'args'):
            args = pred.args
        
        pred_name = pred.name if hasattr(pred, 'name') else str(pred)
        kb.facts.append(KBFact(predicate=pred_name, args=args))
    
    for rule in doc.rules:
        if hasattr(rule, 'variables'):
            variables = [(v.name, v.type_name) if hasattr(v, 'name') else (str(v[0]), str(v[1])) for v in rule.variables]
        else:
            variables = []
        
        # Premise
        if hasattr(rule, 'premise'):
            prem = rule.premise
            prem_name = prem.name if hasattr(prem, 'name') else str(prem)
            prem_args = {}
            if hasattr(prem, 'arguments'):
                for arg in prem.arguments:
                    if hasattr(arg, 'role'):
                        prem_args[arg.role] = arg.value if hasattr(arg, 'value') else str(arg)
        else:
            prem_name = "unknown"
            prem_args = {}
        
        # Conclusion
        if hasattr(rule, 'conclusion'):
            conc = rule.conclusion
            conc_name = conc.name if hasattr(conc, 'name') else str(conc)
            conc_args = {}
            if hasattr(conc, 'arguments'):
                for arg in conc.arguments:
                    if hasattr(arg, 'role'):
                        conc_args[arg.role] = arg.value if hasattr(arg, 'value') else str(arg)
        else:
            conc_name = "unknown"
            conc_args = {}
        
        weight = rule.weight if hasattr(rule, 'weight') else 1.0
        
        kb.rules.append(KBRule(
            variables=variables,
            premise=(prem_name, prem_args),
            conclusion=(conc_name, conc_args),
            weight=weight,
        ))