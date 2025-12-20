# src/qbbn/core/proposition_graph.py
"""
Proposition Graph for QBBN (Section 5).

Bipartite graph:
- Proposition nodes (p): single grounded predicates with probabilities
- Conjunction nodes (g): AND of propositions (premise groups)

Edges connect conjunction nodes to their conclusion propositions.
"""

from dataclasses import dataclass, field
from qbbn.core.logic import Predicate
from qbbn.core.horn import HornClause, KnowledgeBase
from qbbn.core.logical_lang import format_predicate


@dataclass
class PropositionNode:
    """A single proposition with probability."""
    predicate: Predicate
    prob_true: float = 0.5  # P(p=1)
    is_evidence: bool = False  # observed?
    
    @property
    def key(self) -> str:
        """Unique key for this proposition."""
        return format_predicate(self.predicate)
    
    @property
    def prob_false(self) -> float:
        return 1.0 - self.prob_true


@dataclass
class ConjunctionNode:
    """A conjunction of propositions (premise group)."""
    premises: tuple[str, ...]  # keys of premise PropositionNodes
    conclusion: str  # key of conclusion PropositionNode
    
    @property
    def key(self) -> str:
        return f"({' ∧ '.join(self.premises)}) → {self.conclusion}"


@dataclass
class PropositionGraph:
    """
    The proposition graph from Section 5.
    
    Stores propositions and the rules connecting them.
    """
    propositions: dict[str, PropositionNode] = field(default_factory=dict)
    conjunctions: list[ConjunctionNode] = field(default_factory=list)
    
    # Index: which conjunctions feed into each proposition
    incoming: dict[str, list[int]] = field(default_factory=dict)  # prop_key -> [conj indices]
    
    def add_proposition(self, pred: Predicate) -> PropositionNode:
        """Add a proposition node (or return existing)."""
        key = format_predicate(pred)
        if key not in self.propositions:
            self.propositions[key] = PropositionNode(predicate=pred)
            self.incoming[key] = []
        return self.propositions[key]
    
    def add_clause(self, clause: HornClause) -> None:
        """Add a grounded Horn clause to the graph."""
        # Ensure all propositions exist
        premise_keys = []
        for prem in clause.premises:
            node = self.add_proposition(prem)
            premise_keys.append(node.key)
        
        conc_node = self.add_proposition(clause.conclusion)
        
        if clause.is_fact:
            # Facts set evidence
            conc_node.prob_true = 1.0
            conc_node.is_evidence = True
        else:
            # Rules create conjunction nodes
            conj = ConjunctionNode(
                premises=tuple(premise_keys),
                conclusion=conc_node.key,
            )
            conj_idx = len(self.conjunctions)
            self.conjunctions.append(conj)
            self.incoming[conc_node.key].append(conj_idx)
    
    def set_evidence(self, pred: Predicate, value: bool) -> None:
        """Set a proposition as observed evidence."""
        key = format_predicate(pred)
        if key in self.propositions:
            node = self.propositions[key]
            node.prob_true = 1.0 if value else 0.0
            node.is_evidence = True
    
    def get_prob(self, pred: Predicate) -> float:
        """Get probability of a proposition being true."""
        key = format_predicate(pred)
        if key in self.propositions:
            return self.propositions[key].prob_true
        return 0.5  # unknown
    
    @classmethod
    def from_knowledge_base(cls, kb: KnowledgeBase) -> "PropositionGraph":
        """Build graph from a knowledge base."""
        graph = cls()
        for clause in kb.ground_all():
            graph.add_clause(clause)
        return graph
    
    def stats(self) -> dict:
        """Get graph statistics."""
        n_evidence = sum(1 for p in self.propositions.values() if p.is_evidence)
        return {
            "propositions": len(self.propositions),
            "conjunctions": len(self.conjunctions),
            "evidence": n_evidence,
        }
    
    def print_graph(self) -> None:
        """Debug print the graph structure."""
        print(f"=== Propositions ({len(self.propositions)}) ===")
        for key, node in self.propositions.items():
            ev = " [EVIDENCE]" if node.is_evidence else ""
            print(f"  {key}: P={node.prob_true:.2f}{ev}")
        
        print(f"\n=== Conjunctions ({len(self.conjunctions)}) ===")
        for i, conj in enumerate(self.conjunctions):
            print(f"  [{i}] {conj.key}")
        
        print(f"\n=== Incoming edges ===")
        for key, indices in self.incoming.items():
            if indices:
                print(f"  {key} <- {indices}")