# src/qbbn/core/processors.py
"""
Processor registry and base class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import redis
from openai import OpenAI

from qbbn.core.document import DocumentStore


@dataclass
class ProcessorResult:
    success: bool
    message: str


class Processor(ABC):
    name: str
    requires: list[str] = []
    
    def __init__(self, store: DocumentStore, openai_client: OpenAI | None = None):
        self.store = store
        self.openai = openai_client or OpenAI()
    
    def check_requirements(self, doc_id: str) -> tuple[bool, str]:
        """Check if all required stages exist."""
        for req in self.requires:
            if not self.store.has_data(doc_id, req):
                return False, f"Missing required stage: {req}"
        return True, "OK"
    
    def is_done(self, doc_id: str) -> bool:
        """Check if this processor has already run."""
        return self.store.has_data(doc_id, self.name)
    
    @abstractmethod
    def process(self, doc_id: str) -> ProcessorResult:
        """Run the processor."""
        pass
    
    def run(self, doc_id: str, force: bool = False) -> ProcessorResult:
        """Run with checks."""
        if self.is_done(doc_id) and not force:
            return ProcessorResult(True, f"{self.name}: already done (use --force to rerun)")
        
        ok, msg = self.check_requirements(doc_id)
        if not ok:
            return ProcessorResult(False, f"{self.name}: {msg}")
        
        return self.process(doc_id)


# Registry
PROCESSORS: dict[str, type[Processor]] = {}


def register(cls: type[Processor]) -> type[Processor]:
    PROCESSORS[cls.name] = cls
    return cls


def get_processor(name: str, store: DocumentStore, openai_client: OpenAI | None = None) -> Processor:
    if name not in PROCESSORS:
        raise ValueError(f"Unknown processor: {name}. Available: {list(PROCESSORS.keys())}")
    return PROCESSORS[name](store, openai_client)


def list_processors() -> list[str]:
    return list(PROCESSORS.keys())