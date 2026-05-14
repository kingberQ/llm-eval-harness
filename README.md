# LLM Eval Harness

Small dependency-free Python harness for testing LLM workflows before prompt or
model changes reach production.

It evaluates model outputs against JSONL test cases and produces deterministic
scores for:

- required phrases or facts
- forbidden phrases or unsafe claims
- JSON parseability
- required JSON fields
- latency and cost metadata when available

This is intentionally simple enough to run in CI and easy to adapt to product
workflows such as support bots, code review agents, extraction jobs, and internal
automation.

## Quick Start

```bash
python3 src/eval_harness.py \
  --cases examples/cases.jsonl \
  --outputs examples/outputs.jsonl

python3 src/eval_harness.py \
  --cases examples/cases.jsonl \
  --outputs examples/outputs.jsonl \
  --json

python3 test/eval_harness_test.py
```

## Case Format

Each JSONL line is one eval case:

```json
{
  "id": "support-refund-policy",
  "prompt_version": "support-v3",
  "prompt": "Customer asks for a refund after 40 days.",
  "required_contains": ["30-day refund window"],
  "forbidden_contains": ["guaranteed refund"],
  "json_required_fields": []
}
```

Model outputs are also JSONL:

```json
{
  "id": "support-refund-policy",
  "output": "Our policy has a 30-day refund window...",
  "latency_ms": 812,
  "cost_usd": 0.0012
}
```

## Optional Live Model Runner

The harness focuses on evaluation, but it can also call an OpenAI-compatible
chat completions endpoint when `--openai` is set:

```bash
OPENAI_API_KEY=... \
OPENAI_MODEL=gpt-4.1-mini \
python3 src/eval_harness.py --cases examples/cases.jsonl --openai
```

Set `OPENAI_BASE_URL` for compatible providers.

## Why This Exists

AI features regress silently. A prompt that works today can fail after a model
upgrade, a wording tweak, or a new tool schema. This harness makes those changes
measurable before they hit users.
