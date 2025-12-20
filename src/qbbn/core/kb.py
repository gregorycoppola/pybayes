"""
Knowledge Base - loads from a single .logic file or a directory of them.
"""

from pathlib import Path
from dataclasses import dataclass, field
from qbbn.core.logical_lang import parse_logical


@dataclass
class KBEntity:
    id: str
    type: str
    aliases: list[str] = field(default_factory=list)


@dataclass
class KBFact:
    predicate: str
    args: dict[str, str]
    source_file: str = ""


@dataclass
class KBRule:
    variables: list[tuple[str, str]]
    premise: tuple[str, dict[str, str]]
    conclusion: tuple[str, dict[str, str]]
    weight: float = 1.0
    source_file: str = ""


@dataclass 
class KnowledgeBase:
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


def load_kb(path: str | Path) -> KnowledgeBase:
    """
    Load KB from a .logic file or a directory of .logic files.
    """
    path = Path(path)
    kb = KnowledgeBase()
    
    if not path.exists():
        return kb
    
    if path.is_file():
        _load_file(kb, path)
    else:
        # Directory - load all .logic files
        for logic_file in sorted(path.glob("*.logic")):
            _load_file(kb, logic_file)
    
    return kb


def _load_file(kb: KnowledgeBase, path: Path):
    """Parse a .logic file and add to KB."""
    text = path.read_text()
    
    try:
        doc = parse_logical(text)
    except Exception as e:
        print(f"Warning: Failed to parse {path}: {e}")
        return
    
    source = path.name
    
    for ent in doc.entities:
        kb_ent = KBEntity(
            id=ent.name.lower(),
            type=ent.type_name,
            aliases=[ent.name],
        )
        kb.entities[kb_ent.id] = kb_ent
    
    for pred in doc.predicates:
        args = {}
        for arg in pred.arguments:
            args[arg.role] = arg.value.lower() if hasattr(arg, 'value') else str(arg.value)
        
        kb.facts.append(KBFact(predicate=pred.name, args=args, source_file=source))
    
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
            source_file=source,
        ))