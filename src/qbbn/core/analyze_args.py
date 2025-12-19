# src/qbbn/core/analyze_args.py
"""
Step 2: Find arguments and their semantic roles.
"""

import json
from openai import OpenAI

from qbbn.core.analysis import SentenceAnalysis, Argument


SYSTEM_PROMPT = """You are a semantic role labeler.

Given a sentence with numbered tokens and the main verb, identify the arguments.

For each argument, provide:
- role: agent, patient, goal, source, location, instrument, time, manner, etc.
- start: token index (inclusive)
- end: token index (exclusive, so tokens[start:end] gives the span)
- arg_type: np (noun phrase), pp (prepositional phrase), s (clause), etc.

Reply with JSON only:
{
  "arguments": [
    {"role": "agent", "start": 0, "end": 1, "arg_type": "np"},
    {"role": "goal", "start": 2, "end": 5, "arg_type": "pp"}
  ]
}
"""


def build_prompt(tokens: list[str], verb_index: int) -> str:
    numbered = [f"{i}: {t}" for i, t in enumerate(tokens)]
    lines = [
        "Tokens:",
        *numbered,
        "",
        f"Main verb: {tokens[verb_index]} (index {verb_index})",
    ]
    return "\n".join(lines)


def analyze_args(
    tokens: list[str],
    analysis: SentenceAnalysis,
    client: OpenAI | None = None,
) -> SentenceAnalysis:
    """
    Fill in arguments on an existing SentenceAnalysis.
    """
    if analysis.verb_index is None:
        raise ValueError("No verb_index set, run analyze_verb first")
    
    client = client or OpenAI()
    prompt = build_prompt(tokens, analysis.verb_index)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    
    result = json.loads(response.choices[0].message.content)
    
    arguments = [
        Argument(
            role=a["role"],
            start=a["start"],
            end=a["end"],
            arg_type=a["arg_type"],
        )
        for a in result.get("arguments", [])
    ]
    
    analysis.arguments = arguments
    return analysis