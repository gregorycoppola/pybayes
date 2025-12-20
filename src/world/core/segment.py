# src/world/core/segment.py
"""
Segment text into sentences.
"""

import json
from openai import OpenAI


SYSTEM_PROMPT = """You are a sentence segmenter.

Given a text with numbered tokens, identify where each sentence begins and ends.

Important rules:
- "If X then Y" is ONE sentence, not two
- "When X, Y" is ONE sentence
- Sentences end at periods, question marks, or exclamation marks
- If there's no punctuation, the whole text is one sentence
- Include ALL tokens - don't cut off the last word

Reply with JSON:
{
  "sentences": [
    {"start": 0, "end": 5},
    {"start": 5, "end": 12}
  ]
}

Token indices are 0-based. End is exclusive (like Python slices).
For example, if there are 9 tokens (indices 0-8), a single sentence covering all would be {"start": 0, "end": 9}.
"""


def build_prompt(tokens: list[str]) -> str:
    numbered = [f"{i}: {t}" for i, t in enumerate(tokens)]
    lines = [
        "Tokens:",
        *numbered,
        "",
        f"Total tokens: {len(tokens)}",
    ]
    return "\n".join(lines)


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
    
    sentences = [(s["start"], s["end"]) for s in result.get("sentences", [])]
    
    # Safety check: if last sentence doesn't reach the end, extend it
    if sentences and sentences[-1][1] < len(tokens):
        start, _ = sentences[-1]
        sentences[-1] = (start, len(tokens))
    
    # If no sentences detected, treat whole thing as one
    if not sentences:
        sentences = [(0, len(tokens))]
    
    return sentences