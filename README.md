# world

A syntax and semantics parsing pipeline for world models.

Parses natural language into logical forms, grounds them against knowledge bases, and runs Bayesian inference via belief propagation.

**By Super Sonic Vibes ✈️🪩✨**

📖 **[Full documentation and theory →](https://github.com/gregorycoppola/world-docs)**

---

## What is this?

An implementation of the **Quantified Boolean Bayesian Network (QBBN)** — a unified model for logical and probabilistic reasoning. Based on the paper:

> Coppola, G. (2024). *The Quantified Boolean Bayesian Network: Theory and Experiments with a Logical Graphical Model.* [arXiv:2402.06557](https://arxiv.org/abs/2402.06557)

The core idea: express knowledge as weighted logical rules, ground them over entities, build a factor graph, and run belief propagation to answer probabilistic queries.

## Installation

```bash
git clone https://github.com/gregorycoppola/world
cd world
uv sync
```

Requires Redis for document/KB storage:
```bash
brew install redis
brew services start redis
```

## CLI Overview

```bash
world --help
```

Four main commands:
- `world doc` — Document management
- `world kb` — Knowledge base management  
- `world run` — Annotation runs (doc + KB)
- `world layer` — Layer management

## Quick Start

### 1. Start the API server

```bash
uv run uvicorn world.server.main:app --reload
```

### 2. Add a document

```bash
world doc add "If Socrates is a man then Socrates is mortal."
# ✓ Created: 1bb2b620c3c4
```

### 3. Run all NLP layers

```bash
world layer run 1bb2b620c3c4 --all
# ✓ base: 1 sentences, 10 tokens, 0 corrections
# ✓ clauses: 2 clauses
# ✓ args: 4 arguments
# ✓ coref: 1 coreferences
# ✓ entities: 2 entities, 2 types, 0 quantifiers
```

### 4. View the result

```bash
world doc json 1bb2b620c3c4
```

### 5. Add a knowledge base

```bash
world kb add examples/socrates/kb.logic --name socrates
# ✓ Created KB: 6e668c60acc3
```

### 6. Create a run (doc + KB) and process

```bash
world run create 1bb2b620c3c4 6e668c60acc3
# ✓ Created run: 836613b98efe
# ✓ base: cached
# ✓ clauses: cached
# ...
# ✓ link: 1 linked, 0 new
# ✓ logic: generated
# ✓ ground: grounded
```

## Document Commands

```bash
world doc add "Your text here"     # Add a new document
world doc list                      # List all documents
world doc show <doc_id>             # Show document metadata
world doc json <doc_id>             # Show document with all layer data
```

## Knowledge Base Commands

```bash
world kb add <file.logic>           # Add KB from .logic file
world kb add <file.logic> --name x  # Add with custom name
world kb list                       # List all KBs
world kb show <kb_id>               # Show KB details (entities, facts, rules)
world kb dsl <kb_id>                # Export KB as DSL
```

## Layer Commands

```bash
world layer list                    # List all registered layers
world layer run <doc_id> <layer>    # Run a specific layer
world layer run <doc_id> --all      # Run all doc-level layers
world layer run <doc_id> -a -f      # Force re-run all layers
world layer show <doc_id> <layer>   # Show layer as DSL
world layer json <doc_id> <layer>   # Show layer as JSON
world layer set <doc_id> <layer> <file>  # Override layer from file
world layer clear <doc_id> <layer>  # Clear layer override
```

## Run Commands

Runs combine a document with a knowledge base for grounding and inference.

```bash
world run create <doc_id> <kb_id>   # Create and process a run
world run create <doc_id> <kb_id> --no-process  # Create without processing
world run list <doc_id>             # List runs for a document
world run show <run_id>             # Show run info
world run show-all <run_id>         # Show all layer DSLs for a run
world run layer <run_id> <layer>    # Show specific layer DSL
world run process <run_id>          # Process/re-process a run
```

## Layer Pipeline

The NLP pipeline processes documents through these layers:

### Doc-Level Layers (no KB required)

| Layer | Depends On | Description |
|-------|------------|-------------|
| `base` | — | Tokenization, spell correction, sentence segmentation |
| `clauses` | base | Identifies clause structure (antecedent/consequent for conditionals) |
| `args` | base, clauses | Extracts verb arguments (agent, theme, etc.) |
| `coref` | base | Coreference resolution (links mentions of same entity) |
| `entities` | base | Named entity recognition and type extraction |

### Run-Level Layers (require KB)

| Layer | Depends On | Description |
|-------|------------|-------------|
| `link` | entities | Links document entities to KB entities |
| `logic` | clauses, args, link | Generates logical propositions from text |
| `ground` | logic, link, entities | Grounds rules over entities, builds factor graph |

## File Formats

### `.doc` — Document Input

Plain text file containing natural language:

```
If Socrates is a man then Socrates is mortal.
```

### `.logic` — Knowledge Base DSL

```
# Entities
entity socrates : person

# Facts  
man(who: socrates)

# Rules (with optional weights)
rule [x:person]: man(who: x) -> mortal(who: x)
rule [x:person, y:person]: likes(who: x, whom: y) -> friends(a: x, b: y) [0.8]

# Queries
? mortal(who: socrates)
```

## Examples

Example files are in `examples/`:

```
examples/
  socrates/
    input.doc       # "If Socrates is a man..."
    kb.logic        # Entity + rule definitions
  dating/
    input.doc       # Jack/Jill dating scenario
    kb.logic        # Relationship rules
  weather/
    input.doc       # Weather inference chain
    kb.logic        # Causal rules
```

Run an example:

```bash
./scripts/parse "If Socrates is a man then Socrates is mortal."
```

Or with the run-example script:

```bash
./scripts/run-example socrates
```

## Direct Inference

For standalone logical inference without the NLP pipeline:

```bash
uv run world infer examples/socrates.logic
uv run world infer examples/dating_weighted.logic -i 50
```

## API Server

```bash
uv run uvicorn world.server.main:app --reload
```

### Document Endpoints

```
GET  /api/docs                           # List documents
POST /api/docs                           # Create document
GET  /api/docs/{id}                      # Get document
DELETE /api/docs/{id}                    # Delete document
POST /api/docs/{id}/layers/{layer}/run   # Run layer
GET  /api/docs/{id}/layers/{layer}       # Get layer data (JSON)
GET  /api/docs/{id}/layers/{layer}/dsl   # Get layer data (DSL)
PUT  /api/docs/{id}/layers/{layer}       # Set layer override
DELETE /api/docs/{id}/layers/{layer}/override  # Clear override
```

### Knowledge Base Endpoints

```
GET  /api/kbs                            # List KBs
POST /api/kbs                            # Create KB
GET  /api/kbs/{id}                       # Get KB
GET  /api/kbs/{id}/dsl                   # Get KB as DSL
DELETE /api/kbs/{id}                     # Delete KB
```

### Run Endpoints

```
GET  /api/docs/{doc_id}/runs             # List runs for doc
POST /api/runs                           # Create run
GET  /api/runs/{id}                      # Get run with all layer data
POST /api/runs/{id}/process              # Process run
GET  /api/runs/{id}/layers/{layer}/dsl   # Get run layer DSL
```

### Layer Endpoints

```
GET  /api/layers                         # List registered layers
```

## Architecture

```
src/world/
  cli/
    main.py              # Entry point
    client.py            # HTTP client for API
    commands/
      doc.py             # Document commands
      kb.py              # KB commands
      run.py             # Run commands
      layer.py           # Layer commands
  core/
    document.py          # Document storage
    kb.py                # Knowledge base storage/parsing
    run.py               # Run storage
    logical_lang.py      # Types, entities, predicates
    horn.py              # Horn clauses
    factor_graph.py      # Factor graph construction
    inference.py         # Belief propagation
    layers/
      __init__.py        # Layer base class, registry
      runner.py          # Layer execution
      base.py            # Tokenization + segmentation
      clauses.py         # Clause extraction
      args.py            # Argument extraction
      coref.py           # Coreference resolution
      entities.py        # Entity recognition
      link.py            # KB linking
      logic.py           # Logic generation
      ground.py          # Grounding
  server/
    main.py              # FastAPI app
    deps.py              # Dependencies (Redis, OpenAI)
    routes/
      docs.py            # Document routes
      kbs.py             # KB routes
      runs.py            # Run routes
      layers.py          # Layer routes
```

## Environment

Requires:
- Python 3.11+
- Redis
- OpenAI API key (for NLP layers)

```bash
export OPENAI_API_KEY=sk-...
```

## Citation

```bibtex
@article{coppola2024qbbn,
  title={The Quantified Boolean Bayesian Network: Theory and Experiments with a Logical Graphical Model},
  author={Coppola, Greg},
  journal={arXiv preprint arXiv:2402.06557},
  year={2024}
}
```

## License

Apache 2.0
