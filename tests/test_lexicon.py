# tests/test_lexicon.py
"""Tests for lexicon / word sense disambiguation."""

import pytest
import redis

from qbbn.core.lexicon import Lexicon, Sense


@pytest.fixture
def client():
    r = redis.Redis(host="localhost", port=6379, db=15)  # db=15 for tests
    yield r
    # cleanup after each test
    for key in r.scan_iter("testlex:*"):
        r.delete(key)


@pytest.fixture
def lexicon(client):
    return Lexicon(client, prefix="testlex")


def test_sense_symbol():
    sense = Sense("bank", 0, "financial institution")
    assert sense.symbol == "bank.0"


def test_add_first_sense(lexicon):
    sense = lexicon.add("bank", "financial institution")
    
    assert sense.word == "bank"
    assert sense.index == 0
    assert sense.definition == "financial institution"
    assert sense.symbol == "bank.0"


def test_add_multiple_senses(lexicon):
    s0 = lexicon.add("bank", "financial institution")
    s1 = lexicon.add("bank", "river edge")
    
    assert s0.index == 0
    assert s1.index == 1
    assert s0.symbol == "bank.0"
    assert s1.symbol == "bank.1"


def test_lookup_symbol(lexicon):
    lexicon.add("bank", "financial institution")
    lexicon.add("bank", "river edge")
    
    sense = lexicon.lookup_symbol("bank.1")
    
    assert sense is not None
    assert sense.word == "bank"
    assert sense.index == 1
    assert sense.definition == "river edge"


def test_lookup_symbol_not_found(lexicon):
    sense = lexicon.lookup_symbol("nonexistent.0")
    assert sense is None


def test_lookup_word(lexicon):
    lexicon.add("bank", "financial institution")
    lexicon.add("bank", "river edge")
    lexicon.add("river", "flowing water")
    
    senses = lexicon.lookup_word("bank")
    
    assert len(senses) == 2
    assert senses[0].symbol == "bank.0"
    assert senses[1].symbol == "bank.1"


def test_lookup_word_not_found(lexicon):
    senses = lexicon.lookup_word("nonexistent")
    assert senses == []