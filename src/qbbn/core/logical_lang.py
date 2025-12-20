# src/qbbn/core/logical_lang.py

"""
A simple DSL that compiles to our logical primitives.

Syntax:
  entity <name> : <type>
  <pred>(<role>: <arg>, ...)
  rule [<var>:<type>, ...]: <premise> -> <conclusion>
  ? <predicate>  # query
"""

import re
from dataclasses import dataclass, field

from qbbn.core.logic import (
    Type, RoleLabel, Entity, Constant, Variable, Predicate
)
from qbbn.core.implication import ImplicationLink


@dataclass
class LogicalDocument:
    """Parsed logical document."""
    entities: dict[str, Constant] = field(default_factory=dict)
    types: dict[str, Type] = field(default_factory=dict)
    propositions: list[Predicate] = field(default_factory=list)
    rules: list[ImplicationLink] = field(default_factory=list)
    queries: list[Predicate] = field(default_factory=list)


class ParseError(Exception):
    def __init__(self, message: str, line_num: int, line: str):
        self.line_num = line_num
        self.line = line
        super().__init__(f"Line {line_num}: {message}\n  {line}")


class LogicalParser:
    def __init__(self):
        self.doc = LogicalDocument()
    
    def get_or_create_type(self, name: str) -> Type:
        if name not in self.doc.types:
            self.doc.types[name] = Type(name)
        return self.doc.types[name]
    
    def parse(self, text: str) -> LogicalDocument:
        self.doc = LogicalDocument()
        
        lines = text.strip().split("\n")
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            
            try:
                self.parse_line(line, i)
            except Exception as e:
                raise ParseError(str(e), i, line)
        
        return self.doc
    
    def parse_line(self, line: str, line_num: int):
        if line.startswith("entity "):
            self.parse_entity(line)
        elif line.startswith("rule "):
            self.parse_rule(line)
        elif line.startswith("? "):
            self.parse_query(line)
        elif "(" in line:
            self.parse_proposition(line)
        else:
            raise ValueError(f"Unknown syntax: {line}")
    
    def parse_entity(self, line: str):
        """Parse: entity jack : person"""
        match = re.match(r"entity\s+(\w+)\s*:\s*(\w+)", line)
        if not match:
            raise ValueError("Expected: entity <name> : <type>")
        
        name, type_name = match.groups()
        typ = self.get_or_create_type(type_name)
        entity = Entity(name)
        const = Constant(entity, typ)
        self.doc.entities[name] = const
    
    def parse_predicate(self, text: str, allow_variables: bool = False, variables: dict = None) -> Predicate:
        """Parse: pred(role: arg, role: arg)"""
        variables = variables or {}
        
        match = re.match(r"(\w+)\s*\((.*)\)", text.strip())
        if not match:
            raise ValueError(f"Expected predicate: pred(role: arg, ...)")
        
        func_name = match.group(1)
        args_str = match.group(2).strip()
        
        roles = []
        if args_str:
            for arg_part in args_str.split(","):
                arg_part = arg_part.strip()
                role_match = re.match(r"(\w+)\s*:\s*(\w+)", arg_part)
                if not role_match:
                    raise ValueError(f"Expected role: arg, got: {arg_part}")
                
                role_name, arg_name = role_match.groups()
                role = RoleLabel(role_name)
                
                # Is it a variable?
                if arg_name in variables:
                    arg = variables[arg_name]
                # Is it a known entity?
                elif arg_name in self.doc.entities:
                    arg = self.doc.entities[arg_name]
                # Allow variables in rules
                elif allow_variables:
                    raise ValueError(f"Unknown variable: {arg_name}")
                else:
                    raise ValueError(f"Unknown entity: {arg_name}")
                
                roles.append((role, arg))
        
        return Predicate(func_name, tuple(roles))
    
    def parse_proposition(self, line: str):
        """Parse a grounded predicate."""
        pred = self.parse_predicate(line, allow_variables=False)
        self.doc.propositions.append(pred)
    
    def parse_rule(self, line: str):
        """Parse: rule [x:type, y:type]: premise -> conclusion"""
        # Extract variable declarations
        var_match = re.match(r"rule\s*\[(.*?)\]\s*:\s*(.+)", line)
        if not var_match:
            raise ValueError("Expected: rule [var:type, ...]: premise -> conclusion")
        
        var_decls, body = var_match.groups()
        
        # Parse variables
        variables = {}
        var_list = []
        for var_decl in var_decls.split(","):
            var_decl = var_decl.strip()
            if not var_decl:
                continue
            vm = re.match(r"(\w+)\s*:\s*(\w+)", var_decl)
            if not vm:
                raise ValueError(f"Expected var:type, got: {var_decl}")
            var_name, type_name = vm.groups()
            typ = self.get_or_create_type(type_name)
            var = Variable(typ, var_name)
            variables[var_name] = var
            var_list.append(var)
        
        # Parse premise -> conclusion
        if "->" not in body:
            raise ValueError("Expected: premise -> conclusion")
        
        premise_str, conclusion_str = body.split("->", 1)
        
        # Handle conjunction in premise
        if "&" in premise_str:
            # For now, just take first part - TODO: handle conjunction
            premise_str = premise_str.split("&")[0]
        
        premise = self.parse_predicate(premise_str.strip(), allow_variables=True, variables=variables)
        conclusion = self.parse_predicate(conclusion_str.strip(), allow_variables=True, variables=variables)
        
        rule = ImplicationLink(
            premise=premise,
            conclusion=conclusion,
            variables=tuple(var_list),
        )
        self.doc.rules.append(rule)
    
    def parse_query(self, line: str):
        """Parse: ? predicate(...)"""
        pred_str = line[1:].strip()
        pred = self.parse_predicate(pred_str, allow_variables=False)
        self.doc.queries.append(pred)


def parse_logical(text: str) -> LogicalDocument:
    """Parse logical language text into a LogicalDocument."""
    parser = LogicalParser()
    return parser.parse(text)


def format_predicate(pred: Predicate) -> str:
    """Format a predicate for display."""
    args = ", ".join(f"{r.name}: {format_arg(a)}" for r, a in pred.roles)
    return f"{pred.function_name}({args})"


def format_arg(arg) -> str:
    if isinstance(arg, Constant):
        return arg.entity.id
    elif isinstance(arg, Variable):
        return arg.name
    elif isinstance(arg, Predicate):
        return format_predicate(arg)
    return str(arg)


def format_rule(rule: ImplicationLink) -> str:
    vars_str = ", ".join(f"{v.name}:{v.type.name}" for v in rule.variables)
    return f"rule [{vars_str}]: {format_predicate(rule.premise)} -> {format_predicate(rule.conclusion)}"


def format_document(doc: LogicalDocument) -> str:
    """Format a document for display."""
    lines = []
    
    if doc.entities:
        lines.append("# Entities")
        for name, const in doc.entities.items():
            lines.append(f"entity {name} : {const.type.name}")
        lines.append("")
    
    if doc.propositions:
        lines.append("# Propositions")
        for pred in doc.propositions:
            lines.append(format_predicate(pred))
        lines.append("")
    
    if doc.rules:
        lines.append("# Rules")
        for rule in doc.rules:
            lines.append(format_rule(rule))
        lines.append("")
    
    if doc.queries:
        lines.append("# Queries")
        for pred in doc.queries:
            lines.append(f"? {format_predicate(pred)}")
    
    return "\n".join(lines)

