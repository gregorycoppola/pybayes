"""
Base layer - establishes the canonical coordinate system.

Combines: tokenization + spell correction + sentence segmentation.
Output is immutable foundation for all other layers.

Every token is addressable as (sentence_idx, token_idx).
"""

import json
from qbbn.core.layers import Layer, LayerResult, register_layer
from qbbn.core.tokenize import tokenize, Token, SpellCorrector


SEGMENT_PROMPT = """You are a sentence segmenter.

Given numbered tokens, identify where each sentence begins and ends.

Rules:
- "If X then Y" is ONE sentence, not two
- Sentences end at periods, question marks, or exclamation marks
- If no punctuation, the whole text is one sentence
- Include ALL tokens

Reply JSON:
{
  "sentences": [
    {"start": 0, "end": 5},
    {"start": 5, "end": 12}
  ]
}

Token indices are 0-based. End is exclusive (Python slice style).
"""


class BaseLayer(Layer):
    id = "base"
    depends_on = []  # No dependencies - this IS the foundation
    ext = ".base"
    
    def process(self, inputs: dict, context: dict) -> LayerResult:
        doc = inputs.get("_doc")
        if not doc:
            return LayerResult(False, None, "no document")
        
        openai = context.get("openai")
        if not openai:
            return LayerResult(False, None, "no openai client")
        
        # Step 1: Tokenize
        raw_tokens = tokenize(doc.text)
        
        # Step 2: Spell correct
        corrector = SpellCorrector(openai)
        corrected = corrector.correct(raw_tokens)
        
        # Build flat token list with corrections
        flat_tokens = []
        for i, c in enumerate(corrected):
            flat_tokens.append({
                "idx": i,
                "text": c.corrected,
                "original": c.original,
                "char_pos": c.position,
            })
        
        # Step 3: Segment into sentences
        token_texts = [t["text"] for t in flat_tokens]
        
        prompt = "Tokens:\n" + "\n".join(f"{i}: {t}" for i, t in enumerate(token_texts))
        prompt += f"\n\nTotal: {len(token_texts)} tokens (indices 0 to {len(token_texts)-1})"
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SEGMENT_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        
        seg_data = json.loads(response.choices[0].message.content)
        sentence_bounds = seg_data.get("sentences", [])
        
        # Safety: if empty or incomplete, make whole doc one sentence
        if not sentence_bounds:
            sentence_bounds = [{"start": 0, "end": len(flat_tokens)}]
        elif sentence_bounds[-1]["end"] < len(flat_tokens):
            sentence_bounds[-1]["end"] = len(flat_tokens)
        
        # Step 4: Build final structure with (sentence_idx, token_idx) coordinates
        sentences = []
        for sent_idx, bounds in enumerate(sentence_bounds):
            sent_tokens = []
            for flat_idx in range(bounds["start"], bounds["end"]):
                tok = flat_tokens[flat_idx]
                sent_tokens.append({
                    "idx": flat_idx - bounds["start"],  # 0-indexed within sentence
                    "text": tok["text"],
                    "original": tok["original"],
                    "char_pos": tok["char_pos"],
                    "flat_idx": flat_idx,  # Keep for debugging
                })
            
            sentences.append({
                "idx": sent_idx,
                "tokens": sent_tokens,
            })
        
        n_tokens = sum(len(s["tokens"]) for s in sentences)
        n_corrections = sum(1 for t in flat_tokens if t["text"] != t["original"])
        
        return LayerResult(
            True, 
            {"sentences": sentences},
            f"{len(sentences)} sentences, {n_tokens} tokens, {n_corrections} corrections"
        )
    
    def parse_dsl(self, text: str) -> dict:
        """
        Parse:
        # sentence 0
        0: If
        1: someone
        2: is
        ...
        
        # sentence 1
        0: Socrates
        1: is
        ...
        """
        sentences = []
        current_sent = None
        
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("# sentence"):
                if current_sent is not None:
                    sentences.append(current_sent)
                idx = int(line.split()[-1])
                current_sent = {"idx": idx, "tokens": []}
            elif current_sent is not None and ":" in line:
                parts = line.split(":", 1)
                tok_idx = int(parts[0].strip())
                text = parts[1].strip()
                current_sent["tokens"].append({
                    "idx": tok_idx,
                    "text": text,
                    "original": text,
                    "char_pos": 0,
                    "flat_idx": 0,
                })
        
        if current_sent is not None:
            sentences.append(current_sent)
        
        return {"sentences": sentences}
    
    def format_dsl(self, data: dict) -> str:
        lines = []
        for sent in data.get("sentences", []):
            lines.append(f"# sentence {sent['idx']}")
            for tok in sent["tokens"]:
                if tok.get("original") and tok["original"] != tok["text"]:
                    lines.append(f"{tok['idx']}: {tok['text']} (was: {tok['original']})")
                else:
                    lines.append(f"{tok['idx']}: {tok['text']}")
            lines.append("")
        return "\n".join(lines)
    
    def validate(self, data: dict) -> list[str]:
        errors = []
        sentences = data.get("sentences", [])
        
        for sent in sentences:
            for i, tok in enumerate(sent["tokens"]):
                if tok["idx"] != i:
                    errors.append(f"Sentence {sent['idx']}: token {i} has wrong idx {tok['idx']}")
        
        return errors


register_layer(BaseLayer())