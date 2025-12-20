# src/world/core/lexicon.py
"""
Lexicon for word sense disambiguation.

Maps surface words to numbered senses with definitions.
"bank" → "bank.0" (financial), "bank.1" (river edge)

Storage in Redis.
"""

from dataclasses import dataclass
import redis


@dataclass(frozen=True)
class Sense:
    word: str
    index: int
    definition: str

    @property
    def symbol(self) -> str:
        return f"{self.word}.{self.index}"


class Lexicon:
    def __init__(self, client: redis.Redis, prefix: str = "lex"):
        self.client = client
        self.prefix = prefix

    def _sense_key(self, symbol: str) -> str:
        return f"{self.prefix}:sense:{symbol}"

    def _word_key(self, word: str) -> str:
        return f"{self.prefix}:word:{word}"

    def add(self, word: str, definition: str) -> Sense:
        """Add a new sense for a word. Auto-increments index."""
        word_key = self._word_key(word)
        index = self.client.llen(word_key)
        
        sense = Sense(word, index, definition)
        
        # Store definition by symbol
        self.client.set(self._sense_key(sense.symbol), definition)
        
        # Track indices for this word
        self.client.rpush(word_key, index)
        
        return sense

    def lookup_symbol(self, symbol: str) -> Sense | None:
        """Look up a sense by its symbol (e.g., 'bank.1')."""
        definition = self.client.get(self._sense_key(symbol))
        if definition is None:
            return None
        
        parts = symbol.rsplit(".", 1)
        if len(parts) != 2:
            return None
        
        word, index_str = parts
        return Sense(word, int(index_str), definition.decode())

    def lookup_word(self, word: str) -> list[Sense]:
        """Get all senses for a word."""
        word_key = self._word_key(word)
        indices = self.client.lrange(word_key, 0, -1)
        
        senses = []
        for idx_bytes in indices:
            idx = int(idx_bytes.decode())
            symbol = f"{word}.{idx}"
            sense = self.lookup_symbol(symbol)
            if sense:
                senses.append(sense)
        
        return senses

    def clear(self) -> None:
        """Clear all lexicon data. Useful for tests."""
        for key in self.client.scan_iter(f"{self.prefix}:*"):
            self.client.delete(key)