# src/qbbn/core/segment.py
"""
Segment text into sentences.
"""

import json
from openai import OpenAI


SYSTEM_PROMPT = """You are a sentence segmenter.

Given a text with numbered tokens, identify where each sentence begins and ends.

Reply with JSON:
{
  "sentences": [
    {"start": 0, "end": 5},
    {"start": 5, "end": 12}
  ]
}

Token indices are 0-based. End is exclusive (like Python slices).
"""


def build_prompt(tokens: list[str]) -> str:
    numbered = [f"{i}: {t}" for i, t in enumerate(tokens)]
    return "Tokens:\n" + "\n".join(numbered)


def segment_sentences(
    tokens: list[str],
    client: OpenAI | None = None,
) -> list[tuple[int, int]]:
    """
    Returns list of (start, end) token ranges for each sentence.
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
    
    return [(s["start"], s["end"]) for s in result.get("sentences", [])]