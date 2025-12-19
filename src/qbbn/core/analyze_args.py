# src/qbbn/core/analyze_args.py
"""
Step 2: Find arguments and their syntactic types.
Handles recursive sentence arguments.
"""

import json
from openai import OpenAI

from qbbn.core.analysis import SentenceAnalysis, Argument, ArgType


SYSTEM_PROMPT = """You are a syntactic argument identifier.

Given a sentence with numbered tokens and the main verb, identify the arguments.

For each argument, provide:
- role: agent, patient, theme, goal, source, location, instrument, time, manner, etc.
- start: token index (inclusive)
- end: token index (exclusive)
- arg_type: one of: np, s, pp, vp, advp, adjp
  - Use "s" for embedded clauses/sentences (e.g., "that he left", "to go home")
  - Use "np" for noun phrases
  - Use "pp" for prepositional phrases

Reply with JSON only:
{
  "arguments": [
    {"role": "agent", "start": 0, "end": 1, "arg_type": "np"},
    {"role": "theme", "start": 2, "end": 7, "arg_type": "s"}
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
    recursive: bool = True,
) -> SentenceAnalysis:
    """
    Fill in arguments on an existing SentenceAnalysis.
    If recursive=True, will recursively analyze S-type arguments.
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
    
    arguments = []
    for a in result.get("arguments", []):
        arg_type = ArgType(a["arg_type"])
        nested = None
        
        # Recursive analysis for sentence arguments
        if recursive and arg_type == ArgType.S:
            nested_tokens = tokens[a["start"]:a["end"]]
            if nested_tokens:
                from qbbn.core.analyze_verb import analyze_verb
                nested = analyze_verb(nested_tokens, a["start"], a["end"], client)
                nested = analyze_args(nested_tokens, nested, client, recursive=True)
        
        arguments.append(Argument(
            role=a["role"],
            start=a["start"],
            end=a["end"],
            arg_type=arg_type,
            nested=nested,
        ))
    
    analysis.arguments = arguments
    return analysis