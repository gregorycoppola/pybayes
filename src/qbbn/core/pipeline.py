# src/qbbn/core/pipeline.py
"""
Pipeline for processing examples through tokenization, correction, WSD.

Each example is stored in Redis with a UUID handle.
"""

import json
import uuid
from dataclasses import asdict

import redis

from qbbn.core.tokenize import tokenize, Token, SpellCorrector, CorrectedToken


def generate_id() -> str:
    return uuid.uuid4().hex[:12]


class Pipeline:
    def __init__(self, client: redis.Redis, prefix: str = "example"):
        self.client = client
        self.prefix = prefix
        self._corrector = None

    @property
    def corrector(self) -> SpellCorrector:
        if self._corrector is None:
            self._corrector = SpellCorrector()
        return self._corrector

    def _key(self, example_id: str, stage: str) -> str:
        return f"{self.prefix}:{example_id}:{stage}"

    def add(self, text: str) -> str:
        """Add raw text, return UUID."""
        example_id = generate_id()
        self.client.set(self._key(example_id, "raw"), text)
        return example_id

    def get_raw(self, example_id: str) -> str | None:
        raw = self.client.get(self._key(example_id, "raw"))
        return raw.decode() if raw else None

    def run_tokenize(self, example_id: str) -> list[Token]:
        """Tokenize raw text, store result."""
        raw = self.get_raw(example_id)
        if raw is None:
            raise ValueError(f"Example {example_id} not found")

        tokens = tokenize(raw)

        token_dicts = [asdict(t) for t in tokens]
        self.client.set(self._key(example_id, "tokens"), json.dumps(token_dicts))

        return tokens

    def get_tokens(self, example_id: str) -> list[Token] | None:
        data = self.client.get(self._key(example_id, "tokens"))
        if data is None:
            return None
        token_dicts = json.loads(data.decode())
        return [Token(**d) for d in token_dicts]

    def run_correct(self, example_id: str) -> list[CorrectedToken]:
        """Spell correct tokens, store result."""
        tokens = self.get_tokens(example_id)
        if tokens is None:
            raise ValueError(f"Tokens for {example_id} not found, run tokenize first")

        corrected = self.corrector.correct(tokens)

        corrected_dicts = [asdict(c) for c in corrected]
        self.client.set(self._key(example_id, "corrected"), json.dumps(corrected_dicts))

        return corrected

    def get_corrected(self, example_id: str) -> list[CorrectedToken] | None:
        data = self.client.get(self._key(example_id, "corrected"))
        if data is None:
            return None
        corrected_dicts = json.loads(data.decode())
        return [CorrectedToken(**d) for d in corrected_dicts]

    def show(self, example_id: str) -> dict:
        """Get all stages for an example."""
        return {
            "id": example_id,
            "raw": self.get_raw(example_id),
            "tokens": self.get_tokens(example_id),
            "corrected": self.get_corrected(example_id),
        }