# src/qbbn/core/inference.py
"""
Inference for QBBN (Section 7).

Forward chaining: if premises true, conclusion becomes more likely.
"""

from qbbn.core.proposition_graph import PropositionGraph


def forward_chain(graph: PropositionGraph, iterations: int = 10) -> None:
    """
    Simple forward inference.
    
    For each conjunction (A ∧ B → C):
      P(C) increases if P(A) and P(B) are high
    
    This is a simplified version - full belief propagation is more complex.
    """
    for _ in range(iterations):
        changes = 0
        
        for conj in graph.conjunctions:
            # Compute P(premises all true) assuming independence
            premise_prob = 1.0
            for prem_key in conj.premises:
                premise_prob *= graph.propositions[prem_key].prob_true
            
            # Update conclusion using noisy-OR style update
            conc = graph.propositions[conj.conclusion]
            if not conc.is_evidence:
                # P(C) = 1 - (1 - P(C_old)) * (1 - P(premises))
                old_prob = conc.prob_true
                new_prob = 1.0 - (1.0 - old_prob) * (1.0 - premise_prob)
                
                if abs(new_prob - old_prob) > 0.001:
                    changes += 1
                conc.prob_true = new_prob
        
        if changes == 0:
            break


def query(graph: PropositionGraph, pred) -> float:
    """Query the probability of a predicate."""
    from qbbn.core.logical_lang import format_predicate
    key = format_predicate(pred)
    if key in graph.propositions:
        return graph.propositions[key].prob_true
    return 0.0  # not in graph