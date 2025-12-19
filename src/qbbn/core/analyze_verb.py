# src/qbbn/core/analyze_verb.py
"""
Step 1: Find main verb, tense, aspect, mood.
"""

import json
from openai import OpenAI

from qbbn.core.analysis import SentenceAnalysis, Tense, Aspect, Mood


SYSTEM_PROMPT = """You are a syntactic analyzer.

Given a sentence with numbered tokens, identify:
1. The index of the main verb
2. Tense: past, present, or future
3. Aspect: simple, progressive, perfect, or perfect_progressive
4. Mood: indicative, subjunctive, or imperative
5. Whether the verb is negated

Reply with JSON only:
{
  "verb_index": 1,
  "tense": "past",
  "aspect": "simple",
  "mood": "indicative",
  "negated": false
}
"""


def build_prompt(tokens: list[str]) -> str:
    numbered = [f"{i}: {t}" for i, t in enumerate(tokens)]
    return "Tokens:\n" + "\n".join(numbered)


def analyze_verb(
    tokens: list[str],
    start: int,
    end: int,
    client: OpenAI | None = None,
) -> SentenceAnalysis:
    """
    Create a SentenceAnalysis with verb info filled in.
    """
    client = client or OpenAI()
    prompt = build_prompt(tokens)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    
    result = json.loads(response.choices[0].message.content)
    
    tense = Tense(result["tense"]) if result.get("tense") else None
    aspect = Aspect(result["aspect"]) if result.get("aspect") else None
    mood = Mood(result["mood"]) if result.get("mood") else None
    
    return SentenceAnalysis(
        start=start,
        end=end,
        verb_index=result.get("verb_index"),
        tense=tense,
        aspect=aspect,
        mood=mood,
        negated=result.get("negated", False),
    )