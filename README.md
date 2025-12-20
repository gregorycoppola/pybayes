# world

A syntax and semantics parsing pipeline for world models.

Parses natural language into logical forms, grounds them against entities, and runs Bayesian inference via belief propagation.

**By Super Sonic Vibes ✈️🪩✨**

## What is this?

An implementation of the **Quantified Boolean Bayesian Network (QBBN)** — a unified model for logical and probabilistic reasoning. Based on the paper:

> Coppola, G. (2024). *The Quantified Boolean Bayesian Network: Theory and Experiments with a Logical Graphical Model.* [arXiv:2402.06557](https://arxiv.org/abs/2402.06557)

The core idea: express knowledge as weighted logical rules, ground them over entities, build a factor graph, and run belief propagation to answer probabilistic queries.

## Features

- **Logical DSL** — Write rules like `man(x) -> mortal(x) [0.9]`
- **Automatic grounding** — One rule with variables expands to all entity combinations
- **Belief propagation** — Iterative message passing for probabilistic inference
- **NLP pipeline** — Layer-based processing from text to logic (tokenize → clauses → args → coref → logic)
- **FastAPI server** — JSON API for frontend consumption

## Quick Start
```bash
git clone https://github.com/gregorycoppola/world
cd world
uv sync
```

## Examples

**The Socrates syllogism:**
```
# examples/socrates.logic

entity socrates : person

man(theme: socrates)

rule [x:person]: man(theme: x) -> mortal(theme: x)

? mortal(theme: socrates)
```
```bash
uv run world infer examples/socrates.logic
```

**Dating with weights (Section 4.3.2 of the paper):**
```
# examples/dating_weighted.logic

entity jack : person
entity jill : person

lonely(theme: jack)
exciting(theme: jill)
like(agent: jill, theme: jack)

rule [x:person, y:person]: lonely(theme: x) -> like(agent: x, theme: y) [0.3]
rule [x:person, y:person]: exciting(theme: y) -> like(agent: x, theme: y) [0.5]
rule [x:person, y:person]: like(agent: x, theme: y) & like(agent: y, theme: x) -> date(agent: x, theme: y) [0.9]

? date(agent: jack, theme: jill)
```
```bash
uv run world infer examples/dating_weighted.logic -i 50
```

**Chain propagation (Figures 7-9):**
```bash
uv run world infer examples/chain.logic -i 30 --csv results/chain.csv
python scripts/plot_convergence.py results/chain.csv
```

## Architecture
```
src/world/
  cli/              # Command-line interface
  core/
    logical_lang.py # Types, entities, predicates, propositions
    horn.py         # Horn clauses and knowledge base
    factor_graph.py # Factor graph construction
    inference.py    # Belief propagation
    layers/         # NLP processing pipeline
  server/           # FastAPI JSON API
```

## API Server
```bash
uv run uvicorn world.server.main:app --reload
```

Endpoints:
- `GET /api/docs` — List documents
- `GET /api/docs/{id}` — Get document with all layers
- `POST /api/docs/{id}/layers/{layer}/run` — Run a processing layer

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

Apache 2
