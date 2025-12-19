# src/qbbn/core/tokenize.py
"""
Tokenization and spell correction pipeline.

Stage 1: Raw text → tokens
Stage 2: Tokens → spell-corrected tokens (via LLM)
"""

import json
import re
from dataclasses import dataclass
from openai import OpenAI


@dataclass
class Token:
    text: str
    position: int  # character offset in original


@dataclass 
class CorrectedToken:
    original: str
    corrected: str
    position: int


def tokenize(text: str) -> list[Token]:
    """Split text into tokens, tracking positions."""
    tokens = []
    for match in re.finditer(r"\w+|[^\w\s]", text):
        tokens.append(Token(text=match.group(), position=match.start()))
    return tokens


SPELLING_SYSTEM_PROMPT = """You are a spell correction system.

Given a list of tokens, return the corrected spelling for each.
Preserve intentional stylistic choices (names, technical terms).
Only fix clear typos.

Respond with JSON: a list of corrected tokens in the same order.

Example:
Input: ["I", "wentt", "to", "teh", "bank"]
Output: {"tokens": ["I", "went", "to", "the", "bank"]}
"""


class SpellCorrector:
    def __init__(self, openai_client: OpenAI | None = None):
        self.client = openai_client or OpenAI()

    def correct(self, tokens: list[Token]) -> list[CorrectedToken]:
        if not tokens:
            return []

        token_texts = [t.text for t in tokens]

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SPELLING_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(token_texts)},
            ],
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        corrected_texts = result.get("tokens", result)

        # Pair up with originals
        corrected = []
        for token, corrected_text in zip(tokens, corrected_texts):
            corrected.append(CorrectedToken(
                original=token.text,
                corrected=corrected_text,
                position=token.position,
            ))

        return corrected