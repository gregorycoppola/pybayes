# src/qbbn/core/wsd_select.py
"""
WSD Step 1: Given a token and existing senses, pick one or say 'add'.
"""

from openai import OpenAI

from qbbn.core.lexicon import Sense


SYSTEM_PROMPT = """You are a word sense disambiguation system.

Given a word and its possible senses, pick which sense is used in the sentence.
Reply with ONLY the number, or 'add' if none of the senses fit.

Examples:
- Reply: 0
- Reply: 2
- Reply: add
"""


def build_prompt(token: str, sentence: str, senses: list[Sense]) -> str:
    lines = [
        f"Which sense of '{token}' is used in: \"{sentence}\"?",
        "",
    ]
    
    if senses:
        for s in senses:
            lines.append(f"  {s.index}: {s.definition}")
    else:
        lines.append("  (no existing senses)")
    
    lines.append("")
    lines.append("Reply with the number, or 'add' if none fit.")
    
    return "\n".join(lines)


def select_sense(
    token: str,
    sentence: str,
    senses: list[Sense],
    client: OpenAI | None = None,
) -> int | str:
    """
    Returns sense index (int) if picked, or 'add' if new sense needed.
    """
    client = client or OpenAI()
    prompt = build_prompt(token, sentence, senses)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    
    result = response.choices[0].message.content.strip().lower()
    
    if result == "add":
        return "add"
    
    try:
        return int(result)
    except ValueError:
        # LLM gave weird response, default to add
        return "add"