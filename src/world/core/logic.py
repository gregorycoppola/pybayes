# src/qbbn/core/logic.py
"""
Core logical primitives for QBBN.

Tier 1 - Atoms: Type, RoleLabel, Entity
Tier 2 - Simple compositions: Constant, Variable
Tier 3 - Predicates (can be nested for intensionality)
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
    name: str


# Forward reference for recursive Predicate
# Argument can be: Constant, Variable, or Predicate (for intensional args)
Argument = Union[Constant, Variable, "Predicate"]


# === Tier 3: Predicates ===

@dataclass(frozen=True)
class Predicate:
    function_name: str  # e.g., "think.0", "love.0"
    roles: tuple[tuple[RoleLabel, Argument], ...]

    @property
    def is_grounded(self) -> bool:
        """Check if all arguments are grounded (constants or grounded predicates)."""
        for _, arg in self.roles:
            if isinstance(arg, Variable):
                return False
            if isinstance(arg, Predicate) and not arg.is_grounded:
                return False
        return True

    @property
    def variables(self) -> frozenset[Variable]:
        """Get all variables, including in nested predicates."""
        vars = set()
        for _, arg in self.roles:
            if isinstance(arg, Variable):
                vars.add(arg)
            elif isinstance(arg, Predicate):
                vars.update(arg.variables)
        return frozenset(vars)

    def substitute(self, bindings: Dict[Variable, Constant]) -> "Predicate":
        """Replace variables with constants according to bindings."""
        new_roles = []
        for role, arg in self.roles:
            if isinstance(arg, Variable) and arg in bindings:
                new_roles.append((role, bindings[arg]))
            elif isinstance(arg, Predicate):
                new_roles.append((role, arg.substitute(bindings)))
            else:
                new_roles.append((role, arg))
        return Predicate(self.function_name, tuple(new_roles))

    def to_dict(self) -> dict:
        """Serialize to dict for storage."""
        roles_list = []
        for role, arg in self.roles:
            if isinstance(arg, Constant):
                roles_list.append({
                    "role": role.name,
                    "type": "constant",
                    "entity": arg.entity.id,
                    "entity_type": arg.type.name,
                })
            elif isinstance(arg, Variable):
                roles_list.append({
                    "role": role.name,
                    "type": "variable",
                    "var_type": arg.type.name,
                    "var_name": arg.name,
                })
            elif isinstance(arg, Predicate):
                roles_list.append({
                    "role": role.name,
                    "type": "predicate",
                    "predicate": arg.to_dict(),
                })
        return {
            "function_name": self.function_name,
            "roles": roles_list,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Predicate":
        """Deserialize from dict."""
        roles = []
        for r in d["roles"]:
            role = RoleLabel(r["role"])
            if r["type"] == "constant":
                arg = Constant(Entity(r["entity"]), Type(r["entity_type"]))
            elif r["type"] == "variable":
                arg = Variable(Type(r["var_type"]), r["var_name"])
            elif r["type"] == "predicate":
                arg = Predicate.from_dict(r["predicate"])
            roles.append((role, arg))
        return cls(d["function_name"], tuple(roles))


# === Tier 4: Proposition ===

def proposition(predicate: Predicate) -> Predicate:
    """Validate that a predicate is grounded, return it as a Proposition."""
    if not predicate.is_grounded:
        unbound = predicate.variables
        raise ValueError(f"Cannot create proposition: unbound variables {unbound}")
    return predicate


Proposition = Predicate  # type alias for documentation