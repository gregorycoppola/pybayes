"""
Knowledge Base - loads/saves .logic files from a directory.

The KB is read-only during document processing.
Documents link to KB entities but don't modify the KB.
"""

from pathlib import Path
from dataclasses import dataclass, field
from qbbn.core.logical_lang import parse_logical, LogicalDocument


@dataclass
class KBEntity:
    id: str
    type: str
    aliases: list[str] = field(default_factory=list)


@dataclass
class KBFact:
    predicate: str
    args: dict[str, str]  # role -> entity_id
    source_file: str = ""


@dataclass
class KBRule:
    variables: list[tuple[str, str]]  # (var_name, type)
    premise: tuple[str, dict[str, str]]  # (predicate, args)
    conclusion: tuple[str, dict[str, str]]  # (predicate, args)
    weight: float = 1.0
    source_file: str = ""


@dataclass 
class KnowledgeBase:
    """In-memory representation of the KB."""
    entities: dict[str, KBEntity] = field(default_factory=dict)
    facts: list[KBFact] = field(default_factory=list)
    rules: list[KBRule] = field(default_factory=list)
    
    def get_entity(self, id_or_alias: str) -> KBEntity | None:
        """Look up entity by ID or alias."""
        id_lower = id_or_alias.lower()
        
        # Direct ID match
        if id_lower in self.entities:
            return self.entities[id_lower]
        
        # Alias match
        for ent in self.entities.values():
            if id_lower in [a.lower() for a in ent.aliases]:
                return ent
            if id_lower == ent.id.lower():
                return ent
        
        return None
    
    def get_entities_by_type(self, type_name: str) -> list[KBEntity]:
        """Get all entities of a given type."""
        return [e for e in self.entities.values() if e.type == type_name]
    
    def to_logic_text(self) -> str:
        """Export KB as .logic DSL text."""
        lines = []
        
        # Entities
        if self.entities:
            lines.append("# Entities")
            for ent in self.entities.values():
                lines.append(f"entity {ent.id} : {ent.type}")
            lines.append("")
        
        # Facts
        if self.facts:
            lines.append("# Facts")
            for fact in self.facts:
                args_str = ", ".join(f"{k}: {v}" for k, v in fact.args.items())
                lines.append(f"{fact.predicate}({args_str})")
            lines.append("")
        
        # Rules
        if self.rules:
            lines.append("# Rules")
            for rule in self.rules:
                vars_str = ", ".join(f"{v}:{t}" for v, t in rule.variables)
                
                prem_args = ", ".join(f"{k}: {v}" for k, v in rule.premise[1].items())
                prem_str = f"{rule.premise[0]}({prem_args})"
                
                conc_args = ", ".join(f"{k}: {v}" for k, v in rule.conclusion[1].items())
                conc_str = f"{rule.conclusion[0]}({conc_args})"
                
                if rule.weight != 1.0:
                    lines.append(f"rule [{vars_str}]: {prem_str} -> {conc_str} [{rule.weight}]")
                else:
                    lines.append(f"rule [{vars_str}]: {prem_str} -> {conc_str}")
            lines.append("")
        
        return "\n".join(lines)


class KBStore:
    """
    Loads and manages a knowledge base from a directory of .logic files.
    """
    
    def __init__(self, kb_dir: str | Path):
        self.kb_dir = Path(kb_dir)
        self.kb = KnowledgeBase()
    
    def load(self) -> KnowledgeBase:
        """Load all .logic files from the directory."""
        self.kb = KnowledgeBase()
        
        if not self.kb_dir.exists():
            return self.kb
        
        for logic_file in sorted(self.kb_dir.glob("*.logic")):
            self._load_file(logic_file)
        
        return self.kb
    
    def _load_file(self, path: Path):
        """Parse a single .logic file and add to KB."""
        text = path.read_text()
        
        try:
            doc = parse_logical(text)
        except Exception as e:
            print(f"Warning: Failed to parse {path}: {e}")
            return
        
        source = path.name
        
        # Extract entities
        for ent in doc.entities:
            kb_ent = KBEntity(
                id=ent.name.lower(),
                type=ent.type_name,
                aliases=[ent.name],  # Original casing as alias
            )
            self.kb.entities[kb_ent.id] = kb_ent
        
        # Extract facts (grounded predicates)
        for pred in doc.predicates:
            args = {}
            for arg in pred.arguments:
                args[arg.role] = arg.value.lower() if hasattr(arg, 'value') else str(arg.value)
            
            fact = KBFact(
                predicate=pred.name,
                args=args,
                source_file=source,
            )
            self.kb.facts.append(fact)
        
        # Extract rules
        for rule in doc.rules:
            variables = [(v.name, v.type_name) for v in rule.variables]
            
            prem_args = {}
            for arg in rule.premise.arguments:
                prem_args[arg.role] = arg.value if hasattr(arg, 'value') else str(arg.value)
            
            conc_args = {}
            for arg in rule.conclusion.arguments:
                conc_args[arg.role] = arg.value if hasattr(arg, 'value') else str(arg.value)
            
            kb_rule = KBRule(
                variables=variables,
                premise=(rule.premise.name, prem_args),
                conclusion=(rule.conclusion.name, conc_args),
                weight=rule.weight if hasattr(rule, 'weight') else 1.0,
                source_file=source,
            )
            self.kb.rules.append(kb_rule)
    
    def save(self, filename: str = "kb.logic"):
        """Save the entire KB to a single file."""
        self.kb_dir.mkdir(parents=True, exist_ok=True)
        path = self.kb_dir / filename
        path.write_text(self.kb.to_logic_text())
    
    def get_kb(self) -> KnowledgeBase:
        """Return the loaded KB."""
        return self.kb


# Convenience function
def load_kb(kb_dir: str | Path = "kb") -> KnowledgeBase:
    """Load KB from directory."""
    store = KBStore(kb_dir)
    return store.load()