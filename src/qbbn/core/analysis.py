# src/qbbn/core/analysis.py
"""
SentenceAnalysis - built up in steps.

Step 1: main verb + tense
Step 2: arguments with semantic roles
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Argument:
    role: str           # "agent", "patient", "goal", "location", etc.
    start: int          # token index (inclusive)
    end: int            # token index (exclusive)
    arg_type: str       # "np", "s", "pp", etc.


@dataclass
class SentenceAnalysis:
    # Token range this analysis covers
    start: int
    end: int
    
    # Step 1: main verb
    verb_index: int | None = None
    verb_sense: str | None = None  # e.g. "go.0"
    tense: str | None = None       # "past", "present", "future"
    aspect: str | None = None      # "simple", "progressive", "perfect"
    mood: str | None = None        # "indicative", "subjunctive", "imperative"
    negated: bool = False
    
    # Step 2: arguments
    arguments: list[Argument] = field(default_factory=list)