# src/qbbn/core/factor_graph.py
"""
Factor Graph for QBBN (Section 6-7).
"""

import math
import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from qbbn.core.horn import HornClause, KnowledgeBase
from qbbn.core.logical_lang import format_predicate


@dataclass
class VariableNode:
    """A binary variable (proposition)."""
    key: str
    belief: list[float] = field(default_factory=lambda: [0.5, 0.5])
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
    var_keys: list[str]
    weight: float
    factor_type: str
    messages: dict[str, list[float]] = field(default_factory=dict)
    
    def init_messages(self):
        for key in self.var_keys:
            self.messages[key] = [1.0, 1.0]


@dataclass
class FactorGraph:
    """Factor graph for belief propagation."""
    variables: dict[str, VariableNode] = field(default_factory=dict)
    factors: list[FactorNode] = field(default_factory=list)
    var_to_factors: dict[str, list[int]] = field(default_factory=dict)
    
    def add_variable(self, key: str) -> VariableNode:
        if key not in self.variables:
            self.variables[key] = VariableNode(key=key)
            self.var_to_factors[key] = []
        return self.variables[key]
    
    def add_implication_factor(self, premise_key: str, conclusion_key: str, weight: float) -> None:
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
                key = format_predicate(clause.conclusion)
                graph.add_variable(key)
                graph.set_evidence(key, True)
            else:
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
    """Compute φ(assignment) for a factor."""
    if factor.factor_type == "implication":
        premise_key = factor.var_keys[0]
        conclusion_key = factor.var_keys[1]
        premise_val = assignment[premise_key]
        conclusion_val = assignment[conclusion_key]
        
        if premise_val == 1 and conclusion_val == 0:
            return math.exp(-factor.weight)
        return 1.0
    
    elif factor.factor_type == "conjunction_implication":
        conclusion_key = factor.var_keys[-1]
        premise_keys = factor.var_keys[:-1]
        all_premises_true = all(assignment[pk] == 1 for pk in premise_keys)
        conclusion_val = assignment[conclusion_key]
        
        if all_premises_true and conclusion_val == 0:
            return math.exp(-factor.weight)
        return 1.0
    
    return 1.0


@dataclass
class BPTrace:
    """Trace of belief propagation iterations."""
    iterations: list[dict] = field(default_factory=list)
    
    def record(self, iteration: int, graph: "FactorGraph", messages: dict):
        """Record state at this iteration."""
        beliefs = {k: v.prob_true for k, v in graph.variables.items()}
        
        # Extract factor->var messages
        factor_msgs = {}
        for factor in graph.factors:
            for var_key, msg in factor.messages.items():
                factor_msgs[f"f{factor.factor_id}->{var_key}"] = msg[1]  # P(true)
        
        self.iterations.append({
            "iteration": iteration,
            "beliefs": beliefs,
            "factor_messages": factor_msgs,
        })
    
    def to_csv(self, path: str):
        """Write beliefs over iterations to CSV."""
        if not self.iterations:
            return
        
        # Get all variable keys
        var_keys = sorted(self.iterations[0]["beliefs"].keys())
        
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["iteration"] + var_keys)
            
            for it in self.iterations:
                row = [it["iteration"]] + [it["beliefs"].get(k, 0) for k in var_keys]
                writer.writerow(row)
    
    def to_messages_csv(self, path: str):
        """Write messages over iterations to CSV."""
        if not self.iterations:
            return
        
        msg_keys = sorted(self.iterations[0]["factor_messages"].keys())
        
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["iteration"] + msg_keys)
            
            for it in self.iterations:
                row = [it["iteration"]] + [it["factor_messages"].get(k, 0) for k in msg_keys]
                writer.writerow(row)
    
    def print_summary(self):
        """Print convergence summary."""
        if len(self.iterations) < 2:
            return
        
        first = self.iterations[0]["beliefs"]
        last = self.iterations[-1]["beliefs"]
        
        print(f"\nConvergence over {len(self.iterations)} iterations:")
        for key in sorted(first.keys()):
            start = first[key]
            end = last[key]
            delta = end - start
            arrow = "↑" if delta > 0.01 else "↓" if delta < -0.01 else "→"
            print(f"  {key}: {start:.3f} {arrow} {end:.3f} (Δ={delta:+.3f})")


def belief_propagation(graph: FactorGraph, iterations: int = 20, damping: float = 0.5, 
                       trace: BPTrace = None) -> BPTrace:
    """Run loopy belief propagation with optional tracing."""
    if trace is None:
        trace = BPTrace()
    
    # Initialize variable->factor messages
    var_to_factor_msgs: dict[tuple[str, int], list[float]] = {}
    for var_key, factor_indices in graph.var_to_factors.items():
        for fi in factor_indices:
            var_to_factor_msgs[(var_key, fi)] = [1.0, 1.0]
    
    # Record initial state
    trace.record(0, graph, var_to_factor_msgs)
    
    for iteration in range(1, iterations + 1):
        max_change = 0.0
        
        # Update factor -> variable messages
        for factor in graph.factors:
            for target_var in factor.var_keys:
                other_vars = [v for v in factor.var_keys if v != target_var]
                
                new_msg = [0.0, 0.0]
                
                for target_val in [0, 1]:
                    total = 0.0
                    n_other = len(other_vars)
                    
                    for bits in range(2 ** n_other):
                        assignment = {target_var: target_val}
                        for i, ov in enumerate(other_vars):
                            assignment[ov] = (bits >> i) & 1
                        
                        potential = compute_factor_potential(factor, assignment)
                        
                        msg_product = 1.0
                        for ov in other_vars:
                            ov_val = assignment[ov]
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
                for fi in factor_indices:
                    var_to_factor_msgs[(var_key, fi)] = var.belief.copy()
            else:
                for fi in factor_indices:
                    new_msg = [1.0, 1.0]
                    for other_fi in factor_indices:
                        if other_fi != fi:
                            other_factor = graph.factors[other_fi]
                            incoming = other_factor.messages[var_key]
                            new_msg[0] *= incoming[0]
                            new_msg[1] *= incoming[1]
                    
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
                
                b_sum = belief[0] + belief[1]
                if b_sum > 0:
                    var.belief = [belief[0] / b_sum, belief[1] / b_sum]
        
        # Record this iteration
        trace.record(iteration, graph, var_to_factor_msgs)
        
        if max_change < 1e-6:
            break
    
    return trace


def query(graph: FactorGraph, key: str) -> float:
    if key in graph.variables:
        return graph.variables[key].prob_true
    return 0.0
