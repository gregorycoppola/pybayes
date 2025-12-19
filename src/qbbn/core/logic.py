# src/qbbn/core/logic.py
"""
Core logical primitives for QBBN.

Tier 1 - Atoms: Type, RoleLabel, Entity
Tier 2 - Simple compositions: Constant, Variable
Tier 3 - Predicates
Tier 4 - Substitution and grounding
"""

from dataclasses import dataclass
from typing import Dict, Union


# === Tier 1: Atoms ===

@dataclass(frozen=True)
class Type:
    name: str


@dataclass(frozen=True)
class RoleLabel:
    name: str


@dataclass(frozen=True)
class Entity:
    id: str


# === Tier 2: Simple Compositions ===

@dataclass(frozen=True)
class Constant:
    entity: Entity
    type: Type


@dataclass(frozen=True)
class Variable:
    type: Type


Argument = Union[Constant, Variable]


# === Tier 3: Predicates ===

@dataclass(frozen=True)
class Predicate:
    function_name: str
    roles: tuple[tuple[RoleLabel, Argument], ...]

    @property
    def is_grounded(self) -> bool:
        return all(isinstance(arg, Constant) for _, arg in self.roles)

    @property
    def variables(self) -> frozenset[Variable]:
        return frozenset(arg for _, arg in self.roles if isinstance(arg, Variable))

    def substitute(self, bindings: Dict[Variable, Constant]) -> "Predicate":
        """Replace variables with constants according to bindings."""
        new_roles = []
        for role, arg in self.roles:
            if isinstance(arg, Variable) and arg in bindings:
                new_roles.append((role, bindings[arg]))
            else:
                new_roles.append((role, arg))
        return Predicate(self.function_name, tuple(new_roles))


# === Tier 4: Proposition ===

def proposition(predicate: Predicate) -> Predicate:
    """Validate that a predicate is grounded, return it as a Proposition."""
    if not predicate.is_grounded:
        unbound = predicate.variables
        raise ValueError(f"Cannot create proposition: unbound variables {unbound}")
    return predicate


Proposition = Predicate  # type alias for documentation