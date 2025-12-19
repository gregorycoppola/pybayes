# src/qbbn/core/lexicon.py

@dataclass(frozen=True)
class Sense:
    word: str        # "bank"
    index: int       # 0
    definition: str  # "financial institution"
    
    @property
    def symbol(self) -> str:
        return f"{self.word}.{self.index}"

class Lexicon:
    def add(self, word: str, definition: str) -> Sense: ...
    def lookup_symbol(self, symbol: str) -> Sense | None: ...
    def lookup_word(self, word: str) -> list[Sense]: ...