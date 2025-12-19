# tests/test_logic.py
"""Tests for core logical primitives."""

from qbbn.core.logic import (
    Type, RoleLabel, Entity,
    Constant, Variable,
    Predicate,
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
    v1 = Variable(person)
    v2 = Variable(person)
    v3 = Variable(Type("COUNTRY"))
    assert v1 == v2
    assert v1 != v3


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
    
    x_person = Variable(person)
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