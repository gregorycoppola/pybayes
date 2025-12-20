# src/qbbn/core/horn.py
"""
Horn clauses for QBBN.
"""

from dataclasses import dataclass
from itertools import product

from qbbn.core.logic import (
    Type, Constant, Variable, Predicate
)


@dataclass
class HornClause:
    """A Horn clause with weight."""
    premises: tuple[Predicate, ...]
    conclusion: Predicate
    variables: tuple[Variable, ...]
    weight: float = 1.0
    
    @property
    def is_fact(self) -> bool:
        return len(self.premises) == 0
    
    @property
    def is_grounded(self) -> bool:
        for p in self.premises:
            if not p.is_grounded:
                return False
        return self.conclusion.is_grounded
    
    def ground(self, bindings: dict[Variable, Constant]) -> "HornClause":
        new_premises = tuple(p.substitute(bindings) for p in self.premises)
        new_conclusion = self.conclusion.substitute(bindings)
        return HornClause(new_premises, new_conclusion, (), self.weight)
    
    def to_dict(self) -> dict:
        return {
            "premises": [p.to_dict() for p in self.premises],
            "conclusion": self.conclusion.to_dict(),
            "variables": [{"name": v.name, "type": v.type.name} for v in self.variables],
            "weight": self.weight,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "HornClause":
        from qbbn.core.logic import Type
        premises = tuple(Predicate.from_dict(p) for p in d["premises"])
        conclusion = Predicate.from_dict(d["conclusion"])
        variables = tuple(Variable(Type(v["type"]), v["name"]) for v in d["variables"])
        weight = d.get("weight", 1.0)
        return cls(premises, conclusion, variables, weight)


@dataclass
class KnowledgeBase:
    """A collection of Horn clauses and known entities."""
    entities: dict[str, Constant]
    types: dict[str, Type]
    clauses: list[HornClause]
    
    def entities_of_type(self, type_name: str) -> list[Constant]:
        return [c for c in self.entities.values() if c.type.name == type_name]
    
    def add_fact(self, pred: Predicate) -> None:
        clause = HornClause(premises=(), conclusion=pred, variables=(), weight=1.0)
        self.clauses.append(clause)
    
    def add_rule(self, premises: list[Predicate], conclusion: Predicate, 
                 variables: list[Variable], weight: float = 1.0) -> None:
        clause = HornClause(
            premises=tuple(premises),
            conclusion=conclusion,
            variables=tuple(variables),
            weight=weight,
        )
        self.clauses.append(clause)
    
    def ground_all(self) -> list[HornClause]:
        grounded = []
        for clause in self.clauses:
            if clause.is_fact:
                grounded.append(clause)
            else:
                for binding in self._all_bindings(clause.variables):
                    grounded.append(clause.ground(binding))
        return grounded
    
    def _all_bindings(self, variables: tuple[Variable, ...]) -> list[dict[Variable, Constant]]:
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
                weight=rule.weight,
            )
        
        return kb


def format_horn_clause(clause: HornClause, show_vars: bool = True) -> str:
    from qbbn.core.logical_lang import format_predicate
    
    if clause.is_fact:
        return format_predicate(clause.conclusion)
    
    premises_str = " ∧ ".join(format_predicate(p) for p in clause.premises)
    conclusion_str = format_predicate(clause.conclusion)
    weight_str = f" [{clause.weight}]" if clause.weight != 1.0 else ""
    
    if show_vars and clause.variables:
        vars_str = ", ".join(f"{v.name}:{v.type.name}" for v in clause.variables)
        return f"∀[{vars_str}] {premises_str} → {conclusion_str}{weight_str}"
    else:
        return f"{premises_str} → {conclusion_str}{weight_str}"
