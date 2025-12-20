"""
Knowledge Base - stored with UUID, loaded from .logic DSL.
"""

import json
import uuid
from pathlib import Path
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
    
    for ent in doc.entities:
        kb.entities[ent.name.lower()] = KBEntity(
            id=ent.name.lower(),
            type=ent.type_name,
            aliases=[ent.name],
        )
    
    for pred in doc.predicates:
        args = {}
        for arg in pred.arguments:
            args[arg.role] = arg.value.lower() if hasattr(arg, 'value') else str(arg.value)
        kb.facts.append(KBFact(predicate=pred.name, args=args))
    
    for rule in doc.rules:
        variables = [(v.name, v.type_name) for v in rule.variables]
        
        prem_args = {}
        for arg in rule.premise.arguments:
            prem_args[arg.role] = arg.value if hasattr(arg, 'value') else str(arg.value)
        
        conc_args = {}
        for arg in rule.conclusion.arguments:
            conc_args[arg.role] = arg.value if hasattr(arg, 'value') else str(arg.value)
        
        kb.rules.append(KBRule(
            variables=variables,
            premise=(rule.premise.name, prem_args),
            conclusion=(rule.conclusion.name, conc_args),
            weight=rule.weight if hasattr(rule, 'weight') else 1.0,
        ))