# src/world/core/implication.py
"""
Implication structures for QBBN.
"""

from dataclasses import dataclass

from world.core.logic import Predicate, Variable


@dataclass
class ImplicationLink:
    """
    Ψ[variables] premise → conclusion
    
    Example: Ψ[x] man(x) → mortal(x)
    """
    premise: Predicate
    conclusion: Predicate
    variables: tuple[Variable, ...]
    
    def to_dict(self) -> dict:
        return {
            "premise": self.premise.to_dict(),
            "conclusion": self.conclusion.to_dict(),
            "variables": [
                {"type": v.type.name, "name": v.name}
                for v in self.variables
            ],
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "ImplicationLink":
        from world.core.logic import Type
        return cls(
            premise=Predicate.from_dict(d["premise"]),
            conclusion=Predicate.from_dict(d["conclusion"]),
            variables=tuple(
                Variable(Type(v["type"]), v["name"])
                for v in d["variables"]
            ),
        )
    
    def __str__(self) -> str:
        vars_str = ", ".join(v.name for v in self.variables)
        return f"Ψ[{vars_str}] {self.premise.function_name}(...) → {self.conclusion.function_name}(...)"