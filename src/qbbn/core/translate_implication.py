# src/qbbn/core/translate_implication.py
"""
Translate implication analysis to ImplicationLink.
"""

from qbbn.core.analysis import SentenceAnalysis
from qbbn.core.analyze_implication import ImplicationStructure
from qbbn.core.analyze_verb import analyze_verb
from qbbn.core.analyze_args import analyze_args
from qbbn.core.implication import ImplicationLink
from qbbn.core.logic import Predicate, Variable, RoleLabel, Type

from openai import OpenAI


def translate_implication(
    tokens: list[str],
    impl_struct: ImplicationStructure,
    client: OpenAI | None = None,
) -> ImplicationLink:
    """
    Translate an ImplicationStructure to an ImplicationLink.
    """
    client = client or OpenAI()
    
    # Parse antecedent
    ant_tokens = tokens[impl_struct.antecedent_start:impl_struct.antecedent_end]
    ant_analysis = analyze_verb(ant_tokens, impl_struct.antecedent_start, client)
    ant_analysis = analyze_args(ant_tokens, ant_analysis, client, recursive=False)
    
    # Parse consequent
    con_tokens = tokens[impl_struct.consequent_start:impl_struct.consequent_end]
    con_analysis = analyze_verb(con_tokens, impl_struct.consequent_start, client)
    con_analysis = analyze_args(con_tokens, con_analysis, client, recursive=False)
    
    # Build variable map from coreferences
    # Each coreference pair shares a variable
    var_counter = 0
    index_to_var: dict[int, Variable] = {}
    variables = []
    
    for ant_idx, con_idx in impl_struct.coreferences:
        var = Variable(Type("entity"), f"x_{var_counter}")
        var_counter += 1
        index_to_var[ant_idx] = var
        index_to_var[con_idx] = var
        variables.append(var)
    
    # Translate analyses to predicates with variables
    premise = analysis_to_predicate_with_vars(ant_analysis, tokens, index_to_var)
    conclusion = analysis_to_predicate_with_vars(con_analysis, tokens, index_to_var)
    
    return ImplicationLink(
        premise=premise,
        conclusion=conclusion,
        variables=tuple(variables),
    )


def analysis_to_predicate_with_vars(
    analysis: SentenceAnalysis,
    tokens: list[str],
    index_to_var: dict[int, Variable],
) -> Predicate:
    """
    Convert analysis to predicate, using variables where coreferences exist.
    """
    from qbbn.core.logic import Constant, Entity
    
    if analysis.verb_index is None:
        raise ValueError("No verb in analysis")
    
    verb_token = tokens[analysis.verb_index].lower()
    verb_sense = f"{verb_token}.0"
    
    roles = []
    for arg in analysis.arguments:
        role = RoleLabel(arg.role)
        
        # Check if any token in this arg's span has a variable binding
        var_for_arg = None
        for idx in range(arg.start, arg.end):
            if idx in index_to_var:
                var_for_arg = index_to_var[idx]
                break
        
        if var_for_arg:
            roles.append((role, var_for_arg))
        else:
            # No variable - use constant
            span = tokens[arg.start:arg.end]
            head = span[-1].lower() if span else "unknown"
            const = Constant(Entity(f"{head}.0"), Type("entity"))
            roles.append((role, const))
    
    return Predicate(verb_sense, tuple(roles))