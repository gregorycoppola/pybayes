# src/qbbn/core/wsd_define.py
"""
WSD Step 2: Define a new sense for a token.
"""

from openai import OpenAI


SYSTEM_PROMPT = """You are a word sense disambiguation system.

Define the sense of a word as used in a sentence.
Reply with ONLY a brief definition (under 10 words).

Examples:
- "past tense of go; to move toward a place"
- "financial institution for deposits"
- "first person singular pronoun"
"""


def build_prompt(token: str, sentence: str) -> str:
    return f"Define the sense of '{token}' as used in: \"{sentence}\""


def define_sense(
    token: str,
    sentence: str,
    client: OpenAI | None = None,
) -> str:
    """
    Returns a definition string for the new sense.
    """
    client = client or OpenAI()
    prompt = build_prompt(token, sentence)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    
    return response.choices[0].message.content.strip()