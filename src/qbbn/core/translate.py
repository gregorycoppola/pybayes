# src/qbbn/core/translate.py
"""
Translate SentenceAnalysis to Predicate (logical form).
"""

from qbbn.core.analysis import SentenceAnalysis, Argument as SynArg, ArgType
from qbbn.core.logic import Predicate, RoleLabel, Constant, Entity, Type


def translate_np(tokens: list[str], arg: SynArg, senses: list[str] | None) -> Constant:
    """
    Translate an NP argument to a Constant.
    
    For now, uses the head word. Could be smarter about this.
    """
    # Get the tokens for this span
    span_tokens = tokens[arg.start:arg.end]
    
    # Simple heuristic: last word is usually the head for NPs
    head = span_tokens[-1].lower()
    
    # If we have senses, try to find the sense for this token
    sense = f"{head}.0"  # default
    if senses:
        for s in senses:
            if s.startswith(head + "."):
                sense = s
                break
    
    # Guess type from role (rough heuristic)
    type_map = {
        "agent": "entity",
        "patient": "entity", 
        "theme": "entity",
        "goal": "place",
        "source": "place",
        "location": "place",
        "instrument": "thing",
        "time": "time",
    }
    entity_type = type_map.get(arg.role, "entity")
    
    return Constant(Entity(sense), Type(entity_type))


def translate_analysis(
    analysis: SentenceAnalysis,
    tokens: list[str],
    senses: list[str] | None = None,
) -> Predicate:
    """
    Translate a SentenceAnalysis to a Predicate.
    
    Args:
        analysis: The syntactic analysis
        tokens: All tokens (absolute indices)
        senses: WSD senses for tokens (optional)
    
    Returns:
        A Predicate representing the logical form
    """
    # Get verb sense
    if analysis.verb_index is None:
        raise ValueError("No verb in analysis")
    
    verb_token = tokens[analysis.verb_index].lower()
    verb_sense = f"{verb_token}.0"  # default
    if senses and analysis.verb_index < len(senses):
        verb_sense = senses[analysis.verb_index]
    
    # Translate arguments
    roles = []
    for arg in analysis.arguments:
        role = RoleLabel(arg.role)
        
        if arg.arg_type == ArgType.S and arg.nested:
            # Intensional argument - recursive translation
            nested_pred = translate_analysis(arg.nested, tokens, senses)
            roles.append((role, nested_pred))
        
        elif arg.arg_type in (ArgType.NP, ArgType.PP):
            # Entity argument
            const = translate_np(tokens, arg, senses)
            roles.append((role, const))
        
        else:
            # Other types - treat as entity for now
            const = translate_np(tokens, arg, senses)
            roles.append((role, const))
    
    return Predicate(verb_sense, tuple(roles))


def format_predicate(pred: Predicate, indent: int = 0) -> str:
    """Pretty print a predicate."""
    prefix = "  " * indent
    lines = [f"{prefix}{pred.function_name}("]
    
    for role, arg in pred.roles:
        if isinstance(arg, Predicate):
            nested = format_predicate(arg, indent + 1)
            lines.append(f"{prefix}  {role.name}: {nested.strip()},")
        elif isinstance(arg, Constant):
            lines.append(f"{prefix}  {role.name}: {arg.entity.id},")
        else:
            lines.append(f"{prefix}  {role.name}: {arg},")
    
    lines.append(f"{prefix})")
    return "\n".join(lines)