# LLM Eval Harness

A lightweight Python harness for evaluating LLM prompts, outputs, and safety regressions without adding a heavy framework.

The goal is simple: make AI behavior measurable before release. Instead of relying on manual spot checks, keep test cases in files, run them in CI, compare outputs, and catch prompt/model regressions early.

## Problem

LLM features often fail quietly. A prompt change, model upgrade, retrieval change, or tool schema update can make a previously good workflow worse without breaking a normal unit test.

This repo demonstrates a small evaluation loop that is easy to inspect, easy to extend, and suitable for backend teams that need release confidence before shipping AI behavior.

## What It Demonstrates

- File-based eval cases for repeatable testing
- Deterministic checks for required and forbidden output patterns
- Lightweight scoring and pass/fail summaries
- Safety regression checks for prompt output
- CI-friendly command-line execution
- No vendor lock-in in the core harness
- Small enough to adapt into existing Java, Python, or Node backend workflows

## Quick Start

```bash
python -m pytest
python scripts/run_eval.py examples/basic_eval.json
```

Example eval case:

```json
{
  "name": "support_answer_should_be_concise",
  "input": "Explain how to reset a password",
  "checks": {
    "must_include": ["reset", "password"],
    "must_not_include": ["admin token", "private key"]
  }
}
```

## Evaluation Flow

```text
eval cases
   |
   v
prompt/model output
   |
   v
checks and scoring
   |
   v
pass/fail summary for local runs or CI
```

## Where This Fits

This pattern is useful when a team needs to ship AI features with fewer surprises:

- RAG assistants that need answer quality checks
- LLM agents that need tool-call output regression tests
- Prompt pipelines that change frequently
- Model migration work where behavior needs comparison
- CI gates for internal AI tools
- Safety checks for outputs that should avoid secrets, unsafe instructions, or policy violations

## Extension Ideas

- Add multiple model providers behind one adapter interface
- Compare current outputs against golden baselines
- Store eval history as JSON, SQLite, or CI artifacts
- Add semantic similarity checks for less brittle scoring
- Add per-domain validators for code review, support, legal, finance, or ops workflows
- Expose eval runs through a small API or dashboard

## Related Work

This repo is part of my public AI automation portfolio. More context: [GitHub profile](https://github.com/kingberQ) and [LinkedIn](https://www.linkedin.com/in/kingberq/).
