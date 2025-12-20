# src/qbbn/core/horn.py
"""
Horn clauses for QBBN.

A Horn clause: P1 ∧ P2 ∧ ... ∧ Pn → Q
where each Pi and Q are predicates with shared variables.
"""

from dataclasses import dataclass
from itertools import product

from qbbn.core.logic import (
    Type, RoleLabel, Entity, Constant, Variable, Predicate
)


@dataclass
class HornClause:
    """
    A Horn clause: premises → conclusion
    
    All variables must appear in at least one premise.
    """
    premises: tuple[Predicate, ...]
    conclusion: Predicate
    variables: tuple[Variable, ...]
    
    @property
    def is_fact(self) -> bool:
        """A fact has no premises (always true)."""
        return len(self.premises) == 0
    
    @property
    def is_grounded(self) -> bool:
        """Check if all predicates are grounded."""
        for p in self.premises:
            if not p.is_grounded:
                return False
        return self.conclusion.is_grounded
    
    def ground(self, bindings: dict[Variable, Constant]) -> "HornClause":
        """Substitute variables with constants."""
        new_premises = tuple(p.substitute(bindings) for p in self.premises)
        new_conclusion = self.conclusion.substitute(bindings)
        return HornClause(new_premises, new_conclusion, ())
    
    def to_dict(self) -> dict:
        return {
            "premises": [p.to_dict() for p in self.premises],
            "conclusion": self.conclusion.to_dict(),
            "variables": [{"name": v.name, "type": v.type.name} for v in self.variables],
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "HornClause":
        premises = tuple(Predicate.from_dict(p) for p in d["premises"])
        conclusion = Predicate.from_dict(d["conclusion"])
        variables = tuple(Variable(Type(v["type"]), v["name"]) for v in d["variables"])
        return cls(premises, conclusion, variables)


@dataclass
class KnowledgeBase:
    """
    A collection of Horn clauses and known entities.
    
    Can ground rules against entities to produce propositions.
    """
    entities: dict[str, Constant]
    types: dict[str, Type]
    clauses: list[HornClause]
    
    def entities_of_type(self, type_name: str) -> list[Constant]:
        """Get all entities of a given type."""
        return [c for c in self.entities.values() if c.type.name == type_name]
    
    def add_fact(self, pred: Predicate) -> None:
        """Add a grounded fact (Horn clause with no premises)."""
        clause = HornClause(premises=(), conclusion=pred, variables=())
        self.clauses.append(clause)
    
    def add_rule(self, premises: list[Predicate], conclusion: Predicate, variables: list[Variable]) -> None:
        """Add a rule (Horn clause with premises)."""
        clause = HornClause(
            premises=tuple(premises),
            conclusion=conclusion,
            variables=tuple(variables),
        )
        self.clauses.append(clause)
    
    def ground_all(self) -> list[HornClause]:
        """
        Ground all rules by substituting all possible entity combinations.
        
        Returns list of grounded Horn clauses.
        """
        grounded = []
        
        for clause in self.clauses:
            if clause.is_fact:
                grounded.append(clause)
            else:
                for binding in self._all_bindings(clause.variables):
                    grounded_clause = clause.ground(binding)
                    grounded.append(grounded_clause)
        
        return grounded
    
    def _all_bindings(self, variables: tuple[Variable, ...]) -> list[dict[Variable, Constant]]:
        """Generate all possible variable->constant bindings."""
        if not variables:
            return [{}]
        
        domains = []
        for var in variables:
            entities = self.entities_of_type(var.type.name)
            if not entities:
                return []
            domains.append(entities)
        
        bindings = []
        for combo in product(*domains):
            binding = {var: const for var, const in zip(variables, combo)}
            bindings.append(binding)
        
        return bindings
    
    def to_dict(self) -> dict:
        return {
            "entities": {k: {"entity": v.entity.id, "type": v.type.name} for k, v in self.entities.items()},
            "types": list(self.types.keys()),
            "clauses": [c.to_dict() for c in self.clauses],
        }
    
    @classmethod
    def from_logical_document(cls, doc) -> "KnowledgeBase":
        """Create a KnowledgeBase from a parsed LogicalDocument."""
        kb = cls(
            entities=dict(doc.entities),
            types=dict(doc.types),
            clauses=[],
        )
        
        for prop in doc.propositions:
            kb.add_fact(prop)
        
        for rule in doc.rules:
            kb.add_rule(
                premises=rule.premises,
                conclusion=rule.conclusion,
                variables=rule.variables,
            )
        
        return kb


def format_horn_clause(clause: HornClause, show_vars: bool = True) -> str:
    """Format a Horn clause for display."""
    from qbbn.core.logical_lang import format_predicate
    
    if clause.is_fact:
        return format_predicate(clause.conclusion)
    
    premises_str = " ∧ ".join(format_predicate(p) for p in clause.premises)
    conclusion_str = format_predicate(clause.conclusion)
    
    if show_vars and clause.variables:
        vars_str = ", ".join(f"{v.name}:{v.type.name}" for v in clause.variables)
        return f"∀[{vars_str}] {premises_str} → {conclusion_str}"
    else:
        return f"{premises_str} → {conclusion_str}"