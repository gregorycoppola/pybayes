# src/qbbn/core/factor_graph.py
"""
Factor Graph for QBBN (Section 6-7).

Log-linear model: P(x) ∝ exp(-Σ λᵢ fᵢ(x))

For a rule A → B with weight λ:
  - If A=1 and B=0 (violation): cost = λ
  - Otherwise: cost = 0

Factor potential: φ(A,B) = exp(-λ * I[A=1, B=0])
"""

import math
from dataclasses import dataclass, field
from typing import Callable

from qbbn.core.horn import HornClause, KnowledgeBase
from qbbn.core.logical_lang import format_predicate


@dataclass
class VariableNode:
    """A binary variable (proposition)."""
    key: str
    belief: list[float] = field(default_factory=lambda: [0.5, 0.5])  # [P(0), P(1)]
    is_evidence: bool = False
    
    def set_evidence(self, value: bool):
        self.is_evidence = True
        if value:
            self.belief = [0.0, 1.0]
        else:
            self.belief = [1.0, 0.0]
    
    @property
    def prob_true(self) -> float:
        return self.belief[1]


@dataclass 
class FactorNode:
    """A factor connecting variables."""
    factor_id: int
    var_keys: list[str]  # variables this factor connects
    weight: float
    factor_type: str  # "implication" or "conjunction_implication"
    
    # Messages: factor -> variable
    # messages[var_key] = [msg_to_0, msg_to_1]
    messages: dict[str, list[float]] = field(default_factory=dict)
    
    def init_messages(self):
        for key in self.var_keys:
            self.messages[key] = [1.0, 1.0]


@dataclass
class FactorGraph:
    """Factor graph for belief propagation."""
    variables: dict[str, VariableNode] = field(default_factory=dict)
    factors: list[FactorNode] = field(default_factory=list)
    
    # Index: which factors connect to each variable
    var_to_factors: dict[str, list[int]] = field(default_factory=dict)
    
    def add_variable(self, key: str) -> VariableNode:
        if key not in self.variables:
            self.variables[key] = VariableNode(key=key)
            self.var_to_factors[key] = []
        return self.variables[key]
    
    def add_implication_factor(self, premise_key: str, conclusion_key: str, weight: float) -> None:
        """Add factor for: premise → conclusion [weight]"""
        self.add_variable(premise_key)
        self.add_variable(conclusion_key)
        
        factor = FactorNode(
            factor_id=len(self.factors),
            var_keys=[premise_key, conclusion_key],
            weight=weight,
            factor_type="implication",
        )
        factor.init_messages()
        
        factor_idx = len(self.factors)
        self.factors.append(factor)
        self.var_to_factors[premise_key].append(factor_idx)
        self.var_to_factors[conclusion_key].append(factor_idx)
    
    def add_conjunction_factor(self, premise_keys: list[str], conclusion_key: str, weight: float) -> None:
        """Add factor for: p1 ∧ p2 ∧ ... → conclusion [weight]"""
        for pk in premise_keys:
            self.add_variable(pk)
        self.add_variable(conclusion_key)
        
        all_keys = premise_keys + [conclusion_key]
        
        factor = FactorNode(
            factor_id=len(self.factors),
            var_keys=all_keys,
            weight=weight,
            factor_type="conjunction_implication",
        )
        factor.init_messages()
        
        factor_idx = len(self.factors)
        self.factors.append(factor)
        for key in all_keys:
            self.var_to_factors[key].append(factor_idx)
    
    def set_evidence(self, key: str, value: bool) -> None:
        if key in self.variables:
            self.variables[key].set_evidence(value)
    
    @classmethod
    def from_knowledge_base(cls, kb: KnowledgeBase) -> "FactorGraph":
        graph = cls()
        
        for clause in kb.ground_all():
            if clause.is_fact:
                # Facts are evidence
                key = format_predicate(clause.conclusion)
                graph.add_variable(key)
                graph.set_evidence(key, True)
            else:
                # Rules become factors
                premise_keys = [format_predicate(p) for p in clause.premises]
                conclusion_key = format_predicate(clause.conclusion)
                
                if len(premise_keys) == 1:
                    graph.add_implication_factor(premise_keys[0], conclusion_key, clause.weight)
                else:
                    graph.add_conjunction_factor(premise_keys, conclusion_key, clause.weight)
        
        return graph
    
    def stats(self) -> dict:
        n_evidence = sum(1 for v in self.variables.values() if v.is_evidence)
        return {
            "variables": len(self.variables),
            "factors": len(self.factors),
            "evidence": n_evidence,
        }


def compute_factor_potential(factor: FactorNode, assignment: dict[str, int]) -> float:
    """
    Compute φ(assignment) for a factor.
    
    For implication A → B with weight λ:
      - Violation (A=1, B=0): φ = exp(-λ)
      - Otherwise: φ = 1
    
    For conjunction A ∧ B → C with weight λ:
      - Violation (A=1, B=1, C=0): φ = exp(-λ)
      - Otherwise: φ = 1
    """
    if factor.factor_type == "implication":
        premise_key = factor.var_keys[0]
        conclusion_key = factor.var_keys[1]
        
        premise_val = assignment[premise_key]
        conclusion_val = assignment[conclusion_key]
        
        # Violation: premise true but conclusion false
        if premise_val == 1 and conclusion_val == 0:
            return math.exp(-factor.weight)
        return 1.0
    
    elif factor.factor_type == "conjunction_implication":
        conclusion_key = factor.var_keys[-1]
        premise_keys = factor.var_keys[:-1]
        
        # Check if all premises are true
        all_premises_true = all(assignment[pk] == 1 for pk in premise_keys)
        conclusion_val = assignment[conclusion_key]
        
        # Violation: all premises true but conclusion false
        if all_premises_true and conclusion_val == 0:
            return math.exp(-factor.weight)
        return 1.0
    
    return 1.0


def belief_propagation(graph: FactorGraph, iterations: int = 20, damping: float = 0.5) -> None:
    """
    Run loopy belief propagation.
    
    Messages:
      - μ_{f→x}(x): factor f to variable x
      - μ_{x→f}(x): variable x to factor f
    
    Update equations:
      μ_{x→f}(x) = ∏_{g ∈ N(x) \ f} μ_{g→x}(x)
      μ_{f→x}(x) = Σ_{~x} φ(X_f) ∏_{y ∈ X_f \ x} μ_{y→f}(y)
    
    Belief:
      b(x) ∝ ∏_{f ∈ N(x)} μ_{f→x}(x)
    """
    # Initialize variable->factor messages
    var_to_factor_msgs: dict[tuple[str, int], list[float]] = {}
    for var_key, factor_indices in graph.var_to_factors.items():
        for fi in factor_indices:
            var_to_factor_msgs[(var_key, fi)] = [1.0, 1.0]
    
    for iteration in range(iterations):
        max_change = 0.0
        
        # Update factor -> variable messages
        for factor in graph.factors:
            for target_var in factor.var_keys:
                other_vars = [v for v in factor.var_keys if v != target_var]
                
                new_msg = [0.0, 0.0]
                
                # Sum over all assignments to other variables
                for target_val in [0, 1]:
                    total = 0.0
                    
                    # Enumerate assignments to other vars
                    n_other = len(other_vars)
                    for bits in range(2 ** n_other):
                        assignment = {target_var: target_val}
                        for i, ov in enumerate(other_vars):
                            assignment[ov] = (bits >> i) & 1
                        
                        # Factor potential
                        potential = compute_factor_potential(factor, assignment)
                        
                        # Product of incoming messages from other vars
                        msg_product = 1.0
                        for ov in other_vars:
                            ov_val = assignment[ov]
                            # Message from variable to this factor
                            msg = var_to_factor_msgs.get((ov, factor.factor_id), [1.0, 1.0])
                            msg_product *= msg[ov_val]
                        
                        total += potential * msg_product
                    
                    new_msg[target_val] = total
                
                # Normalize
                msg_sum = new_msg[0] + new_msg[1]
                if msg_sum > 0:
                    new_msg = [new_msg[0] / msg_sum, new_msg[1] / msg_sum]
                
                # Damping
                old_msg = factor.messages[target_var]
                damped_msg = [
                    damping * old_msg[0] + (1 - damping) * new_msg[0],
                    damping * old_msg[1] + (1 - damping) * new_msg[1],
                ]
                
                change = abs(damped_msg[0] - old_msg[0]) + abs(damped_msg[1] - old_msg[1])
                max_change = max(max_change, change)
                
                factor.messages[target_var] = damped_msg
        
        # Update variable -> factor messages
        for var_key, factor_indices in graph.var_to_factors.items():
            var = graph.variables[var_key]
            
            if var.is_evidence:
                # Evidence: send fixed message
                for fi in factor_indices:
                    var_to_factor_msgs[(var_key, fi)] = var.belief.copy()
            else:
                for fi in factor_indices:
                    # Product of all incoming factor messages except fi
                    new_msg = [1.0, 1.0]
                    for other_fi in factor_indices:
                        if other_fi != fi:
                            other_factor = graph.factors[other_fi]
                            incoming = other_factor.messages[var_key]
                            new_msg[0] *= incoming[0]
                            new_msg[1] *= incoming[1]
                    
                    # Normalize
                    msg_sum = new_msg[0] + new_msg[1]
                    if msg_sum > 0:
                        new_msg = [new_msg[0] / msg_sum, new_msg[1] / msg_sum]
                    
                    var_to_factor_msgs[(var_key, fi)] = new_msg
        
        # Update beliefs
        for var_key, var in graph.variables.items():
            if not var.is_evidence:
                belief = [1.0, 1.0]
                for fi in graph.var_to_factors[var_key]:
                    factor = graph.factors[fi]
                    msg = factor.messages[var_key]
                    belief[0] *= msg[0]
                    belief[1] *= msg[1]
                
                # Normalize
                b_sum = belief[0] + belief[1]
                if b_sum > 0:
                    var.belief = [belief[0] / b_sum, belief[1] / b_sum]
        
        # Check convergence
        if max_change < 1e-6:
            break


def query(graph: FactorGraph, key: str) -> float:
    if key in graph.variables:
        return graph.variables[key].prob_true
    return 0.0