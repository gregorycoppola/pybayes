# src/qbbn/core/processors_impl.py
"""
Processor implementations.
"""

import json
import re
from qbbn.core.processors import Processor, ProcessorResult, register
from qbbn.core.tokenize import tokenize as do_tokenize


@register
class TokenizeProcessor(Processor):
    name = "tokenize"
    requires = []
    
    def process(self, doc_id: str) -> ProcessorResult:
        doc = self.store.get(doc_id)
        if not doc:
            return ProcessorResult(False, "Document not found")
        
        tokens = do_tokenize(doc.text)
        data = [{"text": t.text, "position": t.position} for t in tokens]
        self.store.set_data(doc_id, self.name, data)
        
        return ProcessorResult(True, f"tokenize: {len(tokens)} tokens")


@register
class CorrectProcessor(Processor):
    name = "correct"
    requires = ["tokenize"]
    
    def process(self, doc_id: str) -> ProcessorResult:
        from qbbn.core.tokenize import Token, SpellCorrector
        
        token_data = self.store.get_data(doc_id, "tokenize")
        tokens = [Token(**t) for t in token_data]
        
        corrector = SpellCorrector(self.openai)
        corrected = corrector.correct(tokens)
        
        data = [{"original": c.original, "corrected": c.corrected, "position": c.position} for c in corrected]
        self.store.set_data(doc_id, self.name, data)
        
        changes = sum(1 for c in corrected if c.original != c.corrected)
        return ProcessorResult(True, f"correct: {changes} corrections")


@register
class ParseClausesProcessor(Processor):
    name = "parse-clauses"
    requires = ["correct"]
    
    def process(self, doc_id: str) -> ProcessorResult:
        correct_data = self.store.get_data(doc_id, "correct")
        tokens = [c["corrected"] for c in correct_data]
        
        prompt = "Tokens:\n" + "\n".join(f"{i}: {t}" for i, t in enumerate(tokens))
        prompt += f"\n\nTotal: {len(tokens)} tokens (indices 0 to {len(tokens)-1})"
        
        response = self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": CLAUSE_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        
        result = json.loads(response.choices[0].message.content)
        self.store.set_data(doc_id, self.name, result)
        
        n_clauses = len(result.get("clauses", []))
        return ProcessorResult(True, f"parse-clauses: {n_clauses} clauses")


@register
class ParseArgsProcessor(Processor):
    name = "parse-args"
    requires = ["correct", "parse-clauses"]
    
    def process(self, doc_id: str) -> ProcessorResult:
        correct_data = self.store.get_data(doc_id, "correct")
        tokens = [c["corrected"] for c in correct_data]
        
        clause_data = self.store.get_data(doc_id, "parse-clauses")
        clauses = clause_data.get("clauses", [])
        
        results = []
        for c in clauses:
            clause_tokens = tokens[c["start"]:c["end"]]
            verb_rel = c["verb_index"] - c["start"]
            
            prompt = "Clause tokens:\n" + "\n".join(f"{i}: {t}" for i, t in enumerate(clause_tokens))
            prompt += f"\n\nVerb: {clause_tokens[verb_rel]} (index {verb_rel})"
            prompt += f"\nTotal: {len(clause_tokens)} tokens"
            
            response = self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": ARG_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            
            args = json.loads(response.choices[0].message.content)
            results.append({
                "clause": c,
                "arguments": args.get("arguments", []),
            })
        
        self.store.set_data(doc_id, self.name, results)
        return ProcessorResult(True, f"parse-args: {len(results)} clauses processed")


# Prompts
CLAUSE_PROMPT = """Identify all clauses in this sentence.

CRITICAL: end index is EXCLUSIVE (Python slice style).
- If tokens are [0:the, 1:dog, 2:ran], and you want "the dog ran", use start=0, end=3 (NOT end=2)
- To include token 8, end must be 9

For "If someone is a man then they are mortal" (tokens 0-8):
- Clause 1: start=1, end=5 → "someone is a man" (verb_index=2)
- Clause 2: start=6, end=9 → "they are mortal" (verb_index=7)
- skip_tokens: [0, 5] → "If", "then"

Reply JSON:
{
  "clauses": [
    {"start": 1, "end": 5, "verb_index": 2, "label": "antecedent"},
    {"start": 6, "end": 9, "verb_index": 7, "label": "consequent"}
  ],
  "skip_tokens": [0, 5]
}
"""

ARG_PROMPT = """Identify arguments of the verb.

CRITICAL: end index is EXCLUSIVE (Python slice style).
- To include token at index 4, end must be 5
- tokens[start:end] should give the full argument

For clause "they are mortal" with verb "are" at index 1:
- agent: start=0, end=1 → "they"  
- theme: start=2, end=3 → "mortal"

Reply JSON:
{
  "arguments": [
    {"start": 0, "end": 1, "role": "agent"},
    {"start": 2, "end": 3, "role": "theme"}
  ]
}

Roles: agent, patient, theme, goal, source, location, instrument, time
"""