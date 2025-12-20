# src/qbbn/core/sentence_lang.py
"""
DSL for sentence structure representation.

Syntax:
  tokens: word word word ...
  clause [start:end] label:
    verb: word [index]
    role: span [start:end]
  skip: index index ...
  coref: index index
"""

import re
from dataclasses import dataclass, field


@dataclass
class Argument:
    role: str
    text: str
    start: int
    end: int


@dataclass
class Clause:
    start: int
    end: int
    label: str
    verb_text: str
    verb_index: int
    arguments: list[Argument] = field(default_factory=list)


@dataclass
class Coreference:
    index_a: int
    index_b: int


@dataclass
class SentenceDocument:
    tokens: list[str] = field(default_factory=list)
    clauses: list[Clause] = field(default_factory=list)
    skip_indices: list[int] = field(default_factory=list)
    coreferences: list[Coreference] = field(default_factory=list)


class SentenceParseError(Exception):
    def __init__(self, message: str, line_num: int, line: str):
        self.line_num = line_num
        self.line = line
        super().__init__(f"Line {line_num}: {message}\n  {line}")


class SentenceParser:
    def __init__(self):
        self.doc = SentenceDocument()
        self.current_clause: Clause | None = None
    
    def parse(self, text: str) -> SentenceDocument:
        self.doc = SentenceDocument()
        self.current_clause = None
        
        lines = text.strip().split("\n")
        for i, line in enumerate(lines, 1):
            line = line.rstrip()
            
            # Skip empty lines and comments
            if not line or line.strip().startswith("#"):
                continue
            
            try:
                self.parse_line(line, i)
            except Exception as e:
                raise SentenceParseError(str(e), i, line)
        
        # Finalize last clause
        if self.current_clause:
            self.doc.clauses.append(self.current_clause)
        
        return self.doc
    
    def parse_line(self, line: str, line_num: int):
        stripped = line.strip()
        
        if stripped.startswith("tokens:"):
            self.parse_tokens(stripped)
        elif stripped.startswith("clause "):
            self.parse_clause_header(stripped)
        elif stripped.startswith("verb:"):
            self.parse_verb(stripped)
        elif stripped.startswith("skip:"):
            self.parse_skip(stripped)
        elif stripped.startswith("coref:"):
            self.parse_coref(stripped)
        elif ":" in stripped and self.current_clause:
            # Argument line (agent:, theme:, goal:, etc.)
            self.parse_argument(stripped)
        else:
            raise ValueError(f"Unknown syntax: {stripped}")
    
    def parse_tokens(self, line: str):
        """Parse: tokens: word word word ..."""
        _, rest = line.split(":", 1)
        self.doc.tokens = rest.strip().split()
    
    def parse_clause_header(self, line: str):
        """Parse: clause [start:end] label:"""
        # Finalize previous clause
        if self.current_clause:
            self.doc.clauses.append(self.current_clause)
        
        match = re.match(r"clause\s+\[(\d+):(\d+)\]\s*(\w*):", line)
        if not match:
            raise ValueError("Expected: clause [start:end] label:")
        
        start, end, label = match.groups()
        self.current_clause = Clause(
            start=int(start),
            end=int(end),
            label=label or "main",
            verb_text="",
            verb_index=-1,
        )
    
    def parse_verb(self, line: str):
        """Parse: verb: word [index]"""
        if not self.current_clause:
            raise ValueError("verb: must be inside a clause")
        
        match = re.match(r"verb:\s*(.+?)\s*\[(\d+)\]", line)
        if not match:
            raise ValueError("Expected: verb: word [index]")
        
        text, index = match.groups()
        self.current_clause.verb_text = text.strip()
        self.current_clause.verb_index = int(index)
    
    def parse_argument(self, line: str):
        """Parse: role: span [start:end]"""
        if not self.current_clause:
            raise ValueError("Argument must be inside a clause")
        
        match = re.match(r"(\w+):\s*(.+?)\s*\[(\d+):(\d+)\]", line)
        if not match:
            raise ValueError("Expected: role: span [start:end]")
        
        role, text, start, end = match.groups()
        arg = Argument(
            role=role.strip(),
            text=text.strip(),
            start=int(start),
            end=int(end),
        )
        self.current_clause.arguments.append(arg)
    
    def parse_skip(self, line: str):
        """Parse: skip: index index ..."""
        _, rest = line.split(":", 1)
        indices = [int(x) for x in rest.strip().split()]
        self.doc.skip_indices = indices
    
    def parse_coref(self, line: str):
        """Parse: coref: index_a index_b"""
        _, rest = line.split(":", 1)
        parts = rest.strip().split()
        if len(parts) != 2:
            raise ValueError("Expected: coref: index_a index_b")
        
        coref = Coreference(int(parts[0]), int(parts[1]))
        self.doc.coreferences.append(coref)


def parse_sentence(text: str) -> SentenceDocument:
    parser = SentenceParser()
    return parser.parse(text)


def format_sentence_doc(doc: SentenceDocument) -> str:
    """Format a sentence document for display."""
    lines = []
    
    lines.append(f"tokens: {' '.join(doc.tokens)}")
    lines.append("")
    
    for clause in doc.clauses:
        lines.append(f"clause [{clause.start}:{clause.end}] {clause.label}:")
        lines.append(f"  verb: {clause.verb_text} [{clause.verb_index}]")
        for arg in clause.arguments:
            lines.append(f"  {arg.role}: {arg.text} [{arg.start}:{arg.end}]")
        lines.append("")
    
    if doc.skip_indices:
        skip_str = " ".join(str(i) for i in doc.skip_indices)
        lines.append(f"skip: {skip_str}")
    
    for coref in doc.coreferences:
        lines.append(f"coref: {coref.index_a} {coref.index_b}")
    
    return "\n".join(lines)


def validate_sentence_doc(doc: SentenceDocument) -> list[str]:
    """Validate a sentence document, return list of errors."""
    errors = []
    n_tokens = len(doc.tokens)
    
    # Track coverage
    covered = set(doc.skip_indices)
    
    for clause in doc.clauses:
        # Check clause bounds
        if clause.start < 0 or clause.end > n_tokens:
            errors.append(f"Clause [{clause.start}:{clause.end}] out of bounds (tokens: 0-{n_tokens})")
        
        # Check verb index
        if clause.verb_index < clause.start or clause.verb_index >= clause.end:
            errors.append(f"Verb index {clause.verb_index} not in clause [{clause.start}:{clause.end}]")
        
        covered.add(clause.verb_index)
        
        # Check arguments
        for arg in clause.arguments:
            if arg.start < clause.start or arg.end > clause.end:
                errors.append(f"Arg {arg.role} [{arg.start}:{arg.end}] not in clause [{clause.start}:{clause.end}]")
            covered.update(range(arg.start, arg.end))
    
    # Check coverage
    missing = [i for i in range(n_tokens) if i not in covered]
    if missing:
        missing_tokens = [(i, doc.tokens[i]) for i in missing]
        errors.append(f"Uncovered tokens: {missing_tokens}")
    
    # Check coreferences
    for coref in doc.coreferences:
        if coref.index_a >= n_tokens or coref.index_b >= n_tokens:
            errors.append(f"Coref indices out of bounds: {coref.index_a}, {coref.index_b}")
    
    return errors