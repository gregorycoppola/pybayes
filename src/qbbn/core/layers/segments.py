# src/qbbn/core/layers/segments.py
"""
Segments layer - sentence boundaries.
"""

import json
from qbbn.core.layers import Layer, LayerResult, register_layer


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


class SegmentsLayer(Layer):
    id = "segments"
    depends_on = ["correct"]
    ext = ".seg"
    
    def process(self, inputs: dict, context: dict) -> LayerResult:
        correct_data = inputs.get("correct", [])
        tokens = [c["corrected"] for c in correct_data]
        
        openai = context.get("openai")
        if not openai:
            return LayerResult(False, None, "no openai client")
        
        prompt = "Tokens:\n" + "\n".join(f"{i}: {t}" for i, t in enumerate(tokens))
        prompt += f"\n\nTotal: {len(tokens)} tokens (indices 0 to {len(tokens)-1})"
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SEGMENT_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        
        data = json.loads(response.choices[0].message.content)
        sentences = data.get("sentences", [])
        
        # Safety: ensure last sentence reaches end
        if sentences and sentences[-1]["end"] < len(tokens):
            sentences[-1]["end"] = len(tokens)
        
        # If empty, whole thing is one sentence
        if not sentences:
            sentences = [{"start": 0, "end": len(tokens)}]
        
        return LayerResult(True, {"sentences": sentences}, f"{len(sentences)} sentences")
    
    def parse_dsl(self, text: str) -> dict:
        """
        Parse:
        [0:9] If someone is a man then they are mortal
        [9:15] She went to the bank .
        """
        import re
        sentences = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            match = re.match(r"\[(\d+):(\d+)\]", line)
            if match:
                start, end = match.groups()
                sentences.append({"start": int(start), "end": int(end)})
        
        return {"sentences": sentences}
    
    def format_dsl(self, data: dict) -> str:
        lines = []
        for s in data.get("sentences", []):
            lines.append(f"[{s['start']}:{s['end']}]")
        return "\n".join(lines)
    
    def validate(self, data: dict) -> list[str]:
        errors = []
        sentences = data.get("sentences", [])
        
        for i, s in enumerate(sentences):
            if s["start"] >= s["end"]:
                errors.append(f"Sentence {i}: invalid bounds [{s['start']}:{s['end']}]")
            
            if i > 0:
                prev = sentences[i-1]
                if s["start"] < prev["end"]:
                    errors.append(f"Sentence {i}: overlaps with previous")
        
        return errors


register_layer(SegmentsLayer())