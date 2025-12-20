# tests/test_logic.py
"""Tests for core logical primitives."""

import pytest

from world.core.logic import (
    Type, RoleLabel, Entity,
    Constant, Variable,
    Predicate,
    proposition,
)


# === Tier 1: Atoms ===

def test_type_equality():
    t1 = Type("PERSON")
    t2 = Type("PERSON")
    t3 = Type("COUNTRY")
    assert t1 == t2
    assert t1 != t3


def test_role_label_equality():
    r1 = RoleLabel("SUBJ")
    r2 = RoleLabel("SUBJ")
    r3 = RoleLabel("DOBJ")
    assert r1 == r2
    assert r1 != r3


def test_entity_equality():
    e1 = Entity("jack")
    e2 = Entity("jack")
    e3 = Entity("jill")
    assert e1 == e2
    assert e1 != e3


# === Tier 2: Simple Compositions ===

def test_constant():
    person = Type("PERSON")
    jack = Entity("jack")
    c1 = Constant(jack, person)
    c2 = Constant(jack, person)
    c3 = Constant(Entity("jill"), person)
    assert c1 == c2
    assert c1 != c3


def test_variable():
    person = Type("PERSON")
    v1 = Variable(person, "x")
    v2 = Variable(person, "x")
    v3 = Variable(person, "y")
    v4 = Variable(Type("COUNTRY"), "x")
    assert v1 == v2
    assert v1 != v3
    assert v1 != v4


# === Tier 3: Predicates ===

def test_predicate_grounded():
    person = Type("PERSON")
    subj = RoleLabel("SUBJ")
    dobj = RoleLabel("DOBJ")
    
    c_jack = Constant(Entity("jack"), person)
    c_jill = Constant(Entity("jill"), person)
    
    pred = Predicate("LIKE", (
        (subj, c_jack),
        (dobj, c_jill),
    ))
    
    assert pred.is_grounded


def test_predicate_not_grounded():
    person = Type("PERSON")
    subj = RoleLabel("SUBJ")
    dobj = RoleLabel("DOBJ")
    
    x_person = Variable(person, "x")
    c_jill = Constant(Entity("jill"), person)
    
    pred = Predicate("LIKE", (
        (subj, x_person),
        (dobj, c_jill),
    ))
    
    assert not pred.is_grounded


def test_predicate_equality():
    person = Type("PERSON")
    subj = RoleLabel("SUBJ")
    c_jack = Constant(Entity("jack"), person)
    
    p1 = Predicate("LIKE", ((subj, c_jack),))
    p2 = Predicate("LIKE", ((subj, c_jack),))
    p3 = Predicate("HATE", ((subj, c_jack),))
    
    assert p1 == p2
    assert p1 != p3


def test_predicate_variables():
    person = Type("PERSON")
    subj = RoleLabel("SUBJ")
    dobj = RoleLabel("DOBJ")
    
    x_person = Variable(person, "x")
    c_jill = Constant(Entity("jill"), person)
    
    pred = Predicate("LIKE", (
        (subj, x_person),
        (dobj, c_jill),
    ))
    
    assert pred.variables == frozenset({x_person})


# === Tier 4: Substitution and Proposition ===

def test_substitute_single_variable():
    person = Type("PERSON")
    subj = RoleLabel("SUBJ")
    dobj = RoleLabel("DOBJ")
    
    x_person = Variable(person, "x")
    c_jack = Constant(Entity("jack"), person)
    c_jill = Constant(Entity("jill"), person)
    
    pred = Predicate("LIKE", (
        (subj, x_person),
        (dobj, c_jill),
    ))
    
    grounded = pred.substitute({x_person: c_jack})
    
    expected = Predicate("LIKE", (
        (subj, c_jack),
        (dobj, c_jill),
    ))
    
    assert grounded == expected


def test_substitute_multiple_variables():
    person = Type("PERSON")
    subj = RoleLabel("SUBJ")
    dobj = RoleLabel("DOBJ")
    
    x_subj = Variable(person, "subj")
    x_dobj = Variable(person, "dobj")
    c_jack = Constant(Entity("jack"), person)
    c_jill = Constant(Entity("jill"), person)
    
    pred = Predicate("LIKE", (
        (subj, x_subj),
        (dobj, x_dobj),
    ))
    
    grounded = pred.substitute({x_subj: c_jack, x_dobj: c_jill})
    
    assert grounded.is_grounded
    assert grounded.roles == ((subj, c_jack), (dobj, c_jill))


def test_substitute_produces_grounded():
    person = Type("PERSON")
    subj = RoleLabel("SUBJ")
    
    x_person = Variable(person, "x")
    c_jack = Constant(Entity("jack"), person)
    
    pred = Predicate("LIKE", ((subj, x_person),))
    grounded = pred.substitute({x_person: c_jack})
    
    assert grounded.is_grounded


def test_substitute_partial():
    person = Type("PERSON")
    subj = RoleLabel("SUBJ")
    dobj = RoleLabel("DOBJ")
    
    x_subj = Variable(person, "subj")
    x_dobj = Variable(person, "dobj")
    c_jack = Constant(Entity("jack"), person)
    
    pred = Predicate("LIKE", (
        (subj, x_subj),
        (dobj, x_dobj),
    ))
    
    partial = pred.substitute({x_subj: c_jack})
    
    assert not partial.is_grounded
    assert partial.variables == frozenset({x_dobj})


def test_proposition_valid():
    person = Type("PERSON")
    subj = RoleLabel("SUBJ")
    c_jack = Constant(Entity("jack"), person)
    
    pred = Predicate("LIKE", ((subj, c_jack),))
    prop = proposition(pred)
    
    assert prop == pred


def test_proposition_invalid():
    person = Type("PERSON")
    subj = RoleLabel("SUBJ")
    x_person = Variable(person, "x")
    
    pred = Predicate("LIKE", ((subj, x_person),))
    
    with pytest.raises(ValueError, match="unbound variables"):
        proposition(pred)