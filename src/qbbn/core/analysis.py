# src/qbbn/core/analysis.py
"""
SentenceAnalysis - built up in steps.

Step 1: main verb + tense
Step 2: arguments with semantic roles
"""

from dataclasses import dataclass, field


@dataclass
class Argument:
    role: str       # "agent", "patient", "goal", "location", etc.
    start: int      # token index (inclusive)
    end: int        # token index (exclusive)
    arg_type: str   # "np", "s", "pp", etc.


@dataclass
class SentenceAnalysis:
    # Token range this analysis covers
    start: int
    end: int
    
    # Step 1: main verb
    verb_index: int | None = None
    verb_sense: str | None = None
    tense: str | None = None
    aspect: str | None = None
    mood: str | None = None
    negated: bool = False
    
    # Step 2: arguments
    arguments: list[Argument] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "verb_index": self.verb_index,
            "verb_sense": self.verb_sense,
            "tense": self.tense,
            "aspect": self.aspect,
            "mood": self.mood,
            "negated": self.negated,
            "arguments": [
                {"role": a.role, "start": a.start, "end": a.end, "arg_type": a.arg_type}
                for a in self.arguments
            ],
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "SentenceAnalysis":
        args = [Argument(**a) for a in d.get("arguments", [])]
        return cls(
            start=d["start"],
            end=d["end"],
            verb_index=d.get("verb_index"),
            verb_sense=d.get("verb_sense"),
            tense=d.get("tense"),
            aspect=d.get("aspect"),
            mood=d.get("mood"),
            negated=d.get("negated", False),
            arguments=args,
        )