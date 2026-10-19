"""Plan or explicitly execute a bounded LLM pilot; no network calls by default."""
import argparse
from dataclasses import asdict
import gzip
import hashlib
import json
import os
from pathlib import Path

from .agents import LLMAgent
from .experiment import expand, provenance, write_csv
from .model import canonical, simulate
from .providers import ResponsesTransport


def plan(spec, max_output_tokens=256):
    if type(max_output_tokens) is not int or max_output_tokens < 16:
        raise ValueError("max_output_tokens must be an integer of at least 16")
    configs, seeds = expand(spec)
    calls = sum(c.ticks * (c.n if c.compute_scaling == "per_agent" else min(c.n, c.compute_budget)) for c in configs) * len(seeds)
    return {"runs": len(configs) * len(seeds), "planned_calls": calls,
            "max_output_tokens_per_call": max_output_tokens, "max_output_tokens_total": calls * max_output_tokens,
            "input_tokens": "unknown until requests are executed", "dollar_cost": "not estimated; select model and pricing first",
            "interpretation": "restricted-choice integration pilot, not free-form multi-agent validation"}


def run_pilot(spec, output, *, model, max_calls, max_output_tokens=256, api_key=None, send=None, source="live"):
    from .providers import http_send
    budget = plan(spec, max_output_tokens)
    if max_calls < budget["planned_calls"]:
        raise ValueError(f"Plan requires {budget['planned_calls']} calls, above max_calls={max_calls}")
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured; no request was made")
    if not model or not model.strip():
        raise ValueError("Select an explicit model before executing")
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory must be empty")
    output.mkdir(parents=True, exist_ok=True)
    transport = ResponsesTransport(model=model, api_key=api_key, audit_path=output / "provider.jsonl",
                                   max_calls=max_calls, max_output_tokens=max_output_tokens, send=send or http_send, source=source)
    agent = LLMAgent(transport, model=model, settings=transport.metadata())
    manifest = provenance() | {"status": "running", "source": source, "sweep": spec, "plan": budget,
                               "agent": agent.metadata(), "completed_runs": 0, "max_calls": max_calls}
    def save_manifest():
        manifest.update(calls_attempted=transport.calls, input_tokens_reported=transport.input_tokens,
                        output_tokens_reported=transport.output_tokens)
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    save_manifest()
    rows = []
    try:
        configs, seeds = expand(spec)
        for config in configs:
            for seed in seeds:
                transport.context = {"config": asdict(config), "seed": seed}
                result = simulate(config, seed, agent)
                events = result.pop("events")
                path = output / result["run_id"]
                with path.with_suffix(".events.jsonl.gz").open("wb") as raw:
                    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
                        stream.write(("\n".join(canonical(e) for e in events) + "\n").encode())
                path.with_suffix(".json").write_text(canonical(result) + "\n", encoding="utf-8")
                decisions = [e for e in events if e["kind"] == "decision"]
                exposed = [e for e in decisions if e["observation"]["exposures"]]
                row = {"run_id": result["run_id"], "seed": seed, "arm": config.arm, "n": config.n,
                       "decisions": len(decisions), "exposed_decisions": len(exposed),
                       "verify_choices": sum(e["decision"]["verify"] for e in decisions),
                       "adopt_choices": sum(e["decision"]["adopt_event"] is not None for e in decisions),
                       **{k: v for k, v in result["metrics"].items() if k != "attributable_offspring"}}
                rows.append(row)
                manifest["completed_runs"] += 1
                write_csv(output / "runs.csv", rows)
                save_manifest()
        manifest["status"] = "complete"
    except Exception as exc:
        manifest.update(status="failed", failure_type=type(exc).__name__)
        raise
    finally:
        manifest["artifacts_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in output.iterdir() if p.is_file() and p.name != "manifest.json"}
        save_manifest()
    return manifest


def mock_send(payload, api_key, timeout):
    """Local always-verify fixture. Token usage is synthetic, never billed."""
    return {"id": "mock-response", "model": "mock-always-verify", "status": "completed",
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": '{"verify":true,"adopt_event":null}'}]}]}, "mock-request"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/llm_smoke.json"))
    parser.add_argument("--output", type=Path, default=Path("results/local-llm"))
    parser.add_argument("--model")
    parser.add_argument("--max-calls", type=int, default=128)
    parser.add_argument("--max-output-tokens", type=int, default=256)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true", help="Make paid API calls; otherwise print the plan only")
    mode.add_argument("--mock", action="store_true", help="Run a local fake provider, with zero network calls")
    args = parser.parse_args()
    try:
        spec = json.loads(args.config.read_text(encoding="utf-8"))
        if args.mock:
            result = run_pilot(spec, args.output, model="mock-always-verify", max_calls=args.max_calls,
                               max_output_tokens=args.max_output_tokens, api_key="mock-not-a-key", send=mock_send, source="mock")
            print(f"MOCK ONLY: {result['completed_runs']} runs, {result['calls_attempted']} fake calls; no LLM evidence or charges.")
        elif args.execute:
            result = run_pilot(spec, args.output, model=args.model, max_calls=args.max_calls, max_output_tokens=args.max_output_tokens)
            print(f"Completed {result['completed_runs']} runs; {result['calls_attempted']} calls. Results: {args.output.resolve()}")
        else:
            print(json.dumps(plan(spec, args.max_output_tokens), indent=2))
    except (ValueError, RuntimeError) as exc:
        parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    main()
