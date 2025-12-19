# src/qbbn/core/logic.py
"""
Core logical primitives for QBBN.

Tier 1 - Atoms: Type, RoleLabel, Entity
Tier 2 - Simple compositions: Constant, Variable
Tier 3 - Predicates
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