# src/qbbn/cli/commands/sent.py
"""
Sentence DSL commands.
"""

from pathlib import Path

from qbbn.core.sentence_lang import (
    parse_sentence, format_sentence_doc, validate_sentence_doc, SentenceParseError
)


def add_subparser(subparsers):
    parser = subparsers.add_parser("sent", help="Sentence structure tools")
    sent_sub = parser.add_subparsers(dest="sent_command", required=True)
    
    # parse
    parse_p = sent_sub.add_parser("parse", help="Parse a .sent file")
    parse_p.add_argument("file", help="Path to .sent file")
    parse_p.set_defaults(func=sent_parse)
    
    # validate
    val_p = sent_sub.add_parser("validate", help="Validate a .sent file")
    val_p.add_argument("file", help="Path to .sent file")
    val_p.set_defaults(func=sent_validate)
    
    # example
    ex_p = sent_sub.add_parser("example", help="Show example syntax")
    ex_p.set_defaults(func=sent_example)


def read_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return p.read_text()


def sent_parse(args):
    try:
        text = read_file(args.file)
        doc = parse_sentence(text)
        
        print(f"=== {args.file} ===\n")
        print(format_sentence_doc(doc))
        
        print(f"\n=== Summary ===")
        print(f"Tokens: {len(doc.tokens)}")
        print(f"Clauses: {len(doc.clauses)}")
        print(f"Coreferences: {len(doc.coreferences)}")
        
    except FileNotFoundError as e:
        print(e)
    except SentenceParseError as e:
        print(f"Parse error: {e}")


def sent_validate(args):
    try:
        text = read_file(args.file)
        doc = parse_sentence(text)
        
        errors = validate_sentence_doc(doc)
        
        if errors:
            print(f"❌ Validation failed for {args.file}:")
            for err in errors:
                print(f"  - {err}")
        else:
            print(f"✓ {args.file} is valid")
            print(f"  {len(doc.tokens)} tokens, {len(doc.clauses)} clauses")
        
    except FileNotFoundError as e:
        print(e)
    except SentenceParseError as e:
        print(f"Parse error: {e}")


def sent_example(args):
    example = """# Example .sent file
# Represents: "If someone is a man then they are mortal"

tokens: If someone is a man then they are mortal

clause [1:5] antecedent:
  verb: is [2]
  agent: someone [1:2]
  theme: a man [3:5]

clause [6:9] consequent:
  verb: are [7]
  agent: they [6:7]
  theme: mortal [8:9]

skip: 0 5

coref: 1 6
"""
    print(example)
```

Create example files:
```
# examples/sentences/mortal.sent

tokens: If someone is a man then they are mortal

clause [1:5] antecedent:
  verb: is [2]
  agent: someone [1:2]
  theme: a man [3:5]

clause [6:9] consequent:
  verb: are [7]
  agent: they [6:7]
  theme: mortal [8:9]

skip: 0 5

coref: 1 6
