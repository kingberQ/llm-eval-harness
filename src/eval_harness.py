#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class EvalCase:
    id: str
    prompt_version: str
    prompt: str
    required_contains: list[str]
    forbidden_contains: list[str]
    json_required_fields: list[str]


@dataclass
class ModelOutput:
    id: str
    output: str
    latency_ms: int | None = None
    cost_usd: float | None = None


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate LLM outputs against JSONL cases.")
    parser.add_argument("--cases", required=True)
    parser.add_argument("--outputs")
    parser.add_argument("--openai", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cases = load_cases(args.cases)
    outputs = run_openai(cases) if args.openai else load_outputs(args.outputs)
    report = evaluate(cases, outputs)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_markdown(report)

    return 0 if report["failed"] == 0 else 1


def load_cases(path: str) -> list[EvalCase]:
    rows = read_jsonl(path)
    cases = []
    for row in rows:
        cases.append(EvalCase(
            id=row["id"],
            prompt_version=row.get("prompt_version", "unknown"),
            prompt=row["prompt"],
            required_contains=row.get("required_contains", []),
            forbidden_contains=row.get("forbidden_contains", []),
            json_required_fields=row.get("json_required_fields", []),
        ))
    return cases


def load_outputs(path: str | None) -> dict[str, ModelOutput]:
    if not path:
        raise SystemExit("--outputs is required unless --openai is used")
    outputs: dict[str, ModelOutput] = {}
    for row in read_jsonl(path):
        outputs[row["id"]] = ModelOutput(
            id=row["id"],
            output=row.get("output", ""),
            latency_ms=row.get("latency_ms"),
            cost_usd=row.get("cost_usd"),
        )
    return outputs


def read_jsonl(path: str) -> list[dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def evaluate(cases: list[EvalCase], outputs: dict[str, ModelOutput]) -> dict[str, Any]:
    results = []
    total_cost = 0.0
    latency_values = []

    for case in cases:
        output = outputs.get(case.id)
        result = evaluate_one(case, output)
        results.append(result)
        if output and output.cost_usd is not None:
            total_cost += output.cost_usd
        if output and output.latency_ms is not None:
            latency_values.append(output.latency_ms)

    passed = sum(1 for item in results if item["passed"])
    failed = len(results) - passed
    return {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "score": round(passed / len(results), 4) if results else 0,
        "total_cost_usd": round(total_cost, 6),
        "avg_latency_ms": round(sum(latency_values) / len(latency_values), 2) if latency_values else None,
        "results": results,
    }


def evaluate_one(case: EvalCase, output: ModelOutput | None) -> dict[str, Any]:
    checks = []
    text = output.output if output else ""

    if output is None:
        checks.append(fail("output_present", "No model output found for case."))
    else:
        checks.append(pass_("output_present"))

    lower_text = text.lower()
    for expected in case.required_contains:
        ok = expected.lower() in lower_text
        checks.append(pass_(f"contains:{expected}") if ok else fail(f"contains:{expected}", "Required text missing."))

    for forbidden in case.forbidden_contains:
        ok = forbidden.lower() not in lower_text
        checks.append(pass_(f"forbidden:{forbidden}") if ok else fail(f"forbidden:{forbidden}", "Forbidden text present."))

    if case.json_required_fields:
        try:
            parsed = json.loads(text)
            for field in case.json_required_fields:
                checks.append(pass_(f"json_field:{field}") if field in parsed else fail(f"json_field:{field}", "Required JSON field missing."))
        except json.JSONDecodeError:
            checks.append(fail("json_parse", "Output is not valid JSON."))

    return {
        "id": case.id,
        "prompt_version": case.prompt_version,
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
        "latency_ms": output.latency_ms if output else None,
        "cost_usd": output.cost_usd if output else None,
    }


def pass_(name: str) -> dict[str, Any]:
    return {"name": name, "passed": True}


def fail(name: str, reason: str) -> dict[str, Any]:
    return {"name": name, "passed": False, "reason": reason}


def run_openai(cases: list[EvalCase]) -> dict[str, ModelOutput]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required for --openai")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    outputs: dict[str, ModelOutput] = {}

    for case in cases:
        started = time.time()
        body = {
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": "Answer exactly for the task. If JSON is requested, return only JSON."},
                {"role": "user", "content": case.prompt},
            ],
        }
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "authorization": f"Bearer {api_key}",
                "content-type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        # Cost varies by provider/model. Keep raw token usage in the output path
        # and let billing code apply the correct price table.
        outputs[case.id] = ModelOutput(
            id=case.id,
            output=content,
            latency_ms=int((time.time() - started) * 1000),
            cost_usd=usage.get("estimated_cost_usd"),
        )
    return outputs


def print_markdown(report: dict[str, Any]) -> None:
    print("# LLM Eval Report")
    print()
    print(f"Score: {report['passed']}/{report['total']} ({report['score'] * 100:.2f}%)")
    print(f"Failed: {report['failed']}")
    print(f"Total cost: ${report['total_cost_usd']:.6f}")
    if report["avg_latency_ms"] is not None:
        print(f"Average latency: {report['avg_latency_ms']} ms")
    print()
    for result in report["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"## {status} {result['id']} ({result['prompt_version']})")
        for check in result["checks"]:
            icon = "ok" if check["passed"] else "fail"
            line = f"- {icon}: {check['name']}"
            if not check["passed"]:
                line += f" - {check['reason']}"
            print(line)
        print()


if __name__ == "__main__":
    sys.exit(main())
