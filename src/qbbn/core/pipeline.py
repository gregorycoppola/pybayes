# src/qbbn/core/pipeline.py
"""
Pipeline for processing examples through tokenization, correction, WSD.
"""

import json
import uuid
from dataclasses import asdict

import redis

from qbbn.core.tokenize import tokenize, Token, SpellCorrector, CorrectedToken
from qbbn.core.state import get_namespace
from qbbn.core.analysis import SentenceAnalysis


def generate_id() -> str:
    return uuid.uuid4().hex[:12]


class Pipeline:
    def __init__(self, client: redis.Redis):
        self.client = client
        self._corrector = None

    @property
    def namespace(self) -> str:
        return get_namespace(self.client)

    @property
    def corrector(self) -> SpellCorrector:
        if self._corrector is None:
            self._corrector = SpellCorrector()
        return self._corrector

    def _key(self, example_id: str, stage: str) -> str:
        return f"{self.namespace}:example:{example_id}:{stage}"

    def add(self, text: str) -> str:
        example_id = generate_id()
        self.client.set(self._key(example_id, "raw"), text)
        return example_id

    def get_raw(self, example_id: str) -> str | None:
        raw = self.client.get(self._key(example_id, "raw"))
        return raw.decode() if raw else None

    def run_tokenize(self, example_id: str) -> list[Token]:
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

    def store_senses(self, example_id: str, symbols: list[str]) -> None:
        self.client.set(self._key(example_id, "senses"), json.dumps(symbols))

    def get_senses(self, example_id: str) -> list[str] | None:
        data = self.client.get(self._key(example_id, "senses"))
        if data is None:
            return None
        return json.loads(data.decode())

    def store_analysis(self, example_id: str, analysis: SentenceAnalysis) -> None:
        self.client.set(self._key(example_id, "analysis"), json.dumps(analysis.to_dict()))

    def get_analysis(self, example_id: str) -> SentenceAnalysis | None:
        data = self.client.get(self._key(example_id, "analysis"))
        if data is None:
            return None
        return SentenceAnalysis.from_dict(json.loads(data.decode()))

    def show(self, example_id: str) -> dict:
        return {
            "id": example_id,
            "raw": self.get_raw(example_id),
            "tokens": self.get_tokens(example_id),
            "corrected": self.get_corrected(example_id),
            "senses": self.get_senses(example_id),
            "analysis": self.get_analysis(example_id),
        }