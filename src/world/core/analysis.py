# src/world/core/analysis.py
"""
SentenceAnalysis - purely syntactic, recursive structure.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ArgType(Enum):
    NP = "np"       # noun phrase - terminal
    S = "s"         # sentence/clause - recursive
    PP = "pp"       # prepositional phrase
    VP = "vp"       # verb phrase
    ADVP = "advp"   # adverb phrase
    ADJP = "adjp"   # adjective phrase


class Tense(Enum):
    PAST = "past"
    PRESENT = "present"
    FUTURE = "future"


class Aspect(Enum):
    SIMPLE = "simple"
    PROGRESSIVE = "progressive"
    PERFECT = "perfect"
    PERFECT_PROGRESSIVE = "perfect_progressive"


class Mood(Enum):
    INDICATIVE = "indicative"
    SUBJUNCTIVE = "subjunctive"
    IMPERATIVE = "imperative"


@dataclass
class Argument:
    role: str                           # "agent", "patient", "theme", "goal", etc.
    start: int                          # token index (inclusive)
    end: int                            # token index (exclusive)
    arg_type: ArgType
    nested: Optional["SentenceAnalysis"] = None  # if arg_type is S
    
    def to_dict(self) -> dict:
        d = {
            "role": self.role,
            "start": self.start,
            "end": self.end,
            "arg_type": self.arg_type.value,
        }
        if self.nested:
            d["nested"] = self.nested.to_dict()
        return d
    
    @classmethod
    def from_dict(cls, d: dict) -> "Argument":
        nested = None
        if "nested" in d and d["nested"]:
            nested = SentenceAnalysis.from_dict(d["nested"])
        return cls(
            role=d["role"],
            start=d["start"],
            end=d["end"],
            arg_type=ArgType(d["arg_type"]),
            nested=nested,
        )


@dataclass
class SentenceAnalysis:
    # Token range this analysis covers
    start: int
    end: int
    
    # Main verb info
    verb_index: int | None = None
    tense: Tense | None = None
    aspect: Aspect | None = None
    mood: Mood | None = None
    negated: bool = False
    
    # Arguments (can be recursive if arg_type is S)
    arguments: list[Argument] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "verb_index": self.verb_index,
            "tense": self.tense.value if self.tense else None,
            "aspect": self.aspect.value if self.aspect else None,
            "mood": self.mood.value if self.mood else None,
            "negated": self.negated,
            "arguments": [a.to_dict() for a in self.arguments],
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "SentenceAnalysis":
        return cls(
            start=d["start"],
            end=d["end"],
            verb_index=d.get("verb_index"),
            tense=Tense(d["tense"]) if d.get("tense") else None,
            aspect=Aspect(d["aspect"]) if d.get("aspect") else None,
            mood=Mood(d["mood"]) if d.get("mood") else None,
            negated=d.get("negated", False),
            arguments=[Argument.from_dict(a) for a in d.get("arguments", [])],
        )


@dataclass
class TextAnalysis:
    """Analysis of a full text - sequence of sentence analyses."""
    sentences: list[SentenceAnalysis] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "sentences": [s.to_dict() for s in self.sentences],
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "TextAnalysis":
        return cls(
            sentences=[SentenceAnalysis.from_dict(s) for s in d.get("sentences", [])],
        )