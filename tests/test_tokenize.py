# tests/test_tokenize.py
"""Tests for tokenization and spell correction."""

import pytest

from qbbn.core.tokenize import tokenize, Token, SpellCorrector, CorrectedToken


# === Tokenizer tests (no LLM) ===

def test_tokenize_simple():
    tokens = tokenize("I went to the bank")
    
    assert len(tokens) == 5
    assert tokens[0] == Token("I", 0)
    assert tokens[1] == Token("went", 2)
    assert tokens[4] == Token("bank", 14)

def test_tokenize_with_punctuation():
    tokens = tokenize("Hello, world!")
    
    assert len(tokens) == 4
    assert tokens[0] == Token("Hello", 0)
    assert tokens[1] == Token(",", 5)
    assert tokens[2] == Token("world", 7)
    assert tokens[3] == Token("!", 12)


def test_tokenize_preserves_case():
    tokens = tokenize("The Cat SAT")
    
    assert tokens[0].text == "The"
    assert tokens[1].text == "Cat"
    assert tokens[2].text == "SAT"


def test_tokenize_multiple_spaces():
    tokens = tokenize("hello    world")
    
    assert len(tokens) == 2
    assert tokens[0] == Token("hello", 0)
    assert tokens[1] == Token("world", 9)


def test_tokenize_empty():
    tokens = tokenize("")
    assert tokens == []


# === Spell correction tests (requires OpenAI) ===

@pytest.mark.skipif(
    not pytest.importorskip("openai"),
    reason="OpenAI not available"
)
def test_spell_correct_typos():
    corrector = SpellCorrector()
    tokens = [
        Token("I", 0),
        Token("wentt", 2),
        Token("to", 8),
        Token("teh", 11),
        Token("bank", 15),
    ]
    
    corrected = corrector.correct(tokens)
    
    assert len(corrected) == 5
    assert corrected[1].original == "wentt"
    assert corrected[1].corrected == "went"
    assert corrected[3].original == "teh"
    assert corrected[3].corrected == "the"


@pytest.mark.skipif(
    not pytest.importorskip("openai"),
    reason="OpenAI not available"
)
def test_spell_correct_preserves_correct_words():
    corrector = SpellCorrector()
    tokens = [Token("hello", 0), Token("world", 6)]
    
    corrected = corrector.correct(tokens)
    
    assert corrected[0].corrected == "hello"
    assert corrected[1].corrected == "world"


@pytest.mark.skipif(
    not pytest.importorskip("openai"),
    reason="OpenAI not available"
)
def test_spell_correct_empty():
    corrector = SpellCorrector()
    corrected = corrector.correct([])
    assert corrected == []
