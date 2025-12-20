# src/world/core/analyze_implication.py
"""
Analyze a sentence to detect if it's an implication.
"""

import json
from dataclasses import dataclass
from openai import OpenAI


SYSTEM_PROMPT = """You are a logical structure analyzer.

Given a sentence, determine if it expresses an implication (a general rule).

Implication patterns:
- "If X, then Y" - conditional
- "All X are Y" - universal
- "When X, Y" - conditional
- "X implies Y" - explicit
- Generic statements like "Dogs bark" (implicitly: all dogs bark)

If it IS an implication, identify:
1. The antecedent (premise/condition) - token range [start, end)
2. The consequent (conclusion/result) - token range [start, end)
3. Coreference pairs - which words in antecedent refer to same entity as words in consequent

Reply with JSON:
{
  "is_implication": true,
  "antecedent": {"start": 0, "end": 4},
  "consequent": {"start": 5, "end": 8},
  "coreferences": [
    {"antecedent_index": 1, "consequent_index": 6}
  ]
}

If NOT an implication:
{
  "is_implication": false
}
"""


def build_prompt(tokens: list[str]) -> str:
    numbered = [f"{i}: {t}" for i, t in enumerate(tokens)]
    return "Tokens:\n" + "\n".join(numbered)


@dataclass
class ImplicationStructure:
    """Raw implication structure before full analysis."""
    antecedent_start: int
    antecedent_end: int
    consequent_start: int
    consequent_end: int
    coreferences: list[tuple[int, int]]  # (antecedent_idx, consequent_idx)


def analyze_implication(
    tokens: list[str],
    client: OpenAI | None = None,
) -> ImplicationStructure | None:
    """
    Check if tokens form an implication. Return structure if so.
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
    
    if not result.get("is_implication"):
        return None
    
    corefs = [
        (c["antecedent_index"], c["consequent_index"])
        for c in result.get("coreferences", [])
    ]
    
    return ImplicationStructure(
        antecedent_start=result["antecedent"]["start"],
        antecedent_end=result["antecedent"]["end"],
        consequent_start=result["consequent"]["start"],
        consequent_end=result["consequent"]["end"],
        coreferences=corefs,
    )