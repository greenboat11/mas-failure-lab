"""Common sweep CLI for Experiments 2 and 3; Experiment 1 keeps its stable CLI."""
import argparse
from dataclasses import asdict
import gzip
import hashlib
import itertools
import json
from pathlib import Path

from . import composition, oversight
from .statistics import interval
from .provenance import provenance
from .runner import write_csv, write_run
from .randomness import seed_plan
from .model import canonical
from .diagnostics import composition_metrics, oversight_metrics

ENGINES = {"composition": (composition.CompositionConfig, composition.simulate,
                            ("global_violation", "locally_compliant_violation", "publication_blocked", "authorized_task_completion")),
           "oversight": (oversight.OversightConfig, oversight.simulate,
                         ("unsafe_fraction", "final_backlog", "pending_at_horizon", "wasted_reviews", "original_review_demand", "retry_demand", "stale_requests"))}


def expand(experiment, spec):
    if experiment not in ENGINES:
        raise ValueError("unknown experiment")
    if set(spec) - {"base", "axes", "seeds"}:
        raise ValueError("unknown sweep fields")
    seeds = spec["seeds"]
    if not seeds or any(type(s) is not int or s < 0 for s in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be unique nonnegative integers")
    axes = spec.get("axes", {})
    names = sorted(axes)
    if any(not values or len({canonical(v) for v in values}) != len(values) for values in axes.values()):
        raise ValueError("axes must be nonempty and unique")
    cls = ENGINES[experiment][0]
    return [cls(**(spec.get("base", {}) | dict(zip(names, values)))) for values in itertools.product(*(axes[n] for n in names))], seeds


def run_sweep(experiment, spec, output, plots=True):
    configs, seeds = expand(experiment, spec)
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory must be empty")
    output.mkdir(parents=True, exist_ok=True)
    (output / "runs").mkdir()
    manifest = provenance() | {"experiment": experiment, "engine_version": 1, "source": "scripted",
                               "sweep": spec, "status": "running", "completed_runs": 0}
    def save():
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    save()
    manifest["seed_plans"] = [{"config": asdict(c), "base_seed": s, **seed_plan(c, s)} for c in configs for s in seeds]
    rows, summaries, trajectories = [], [], []
    try:
        for config in configs:
            group = []
            for seed in seeds:
                result = ENGINES[experiment][1](config, seed)
                additions = composition_metrics(result) if experiment == "composition" else oversight_metrics(config, result)
                for key, value in additions.items():
                    result["metrics"].setdefault(key, value)
                path = output / "runs" / result["run_id"]
                write_run(path, result)
                row = {"run_id": result["run_id"], "seed": seed, **asdict(config), **result["metrics"]}
                rows.append(row)
                group.append(row)
                trajectories.append(result)
                manifest["completed_runs"] += 1
            summary = asdict(config) | {"replicates": len(seeds)}
            if experiment == "oversight":
                summary.update({key: group[0][key] for key in ("rho_0", "rho_0_status", "nominal_offered_review_load")})
            for metric in ENGINES[experiment][2]:
                mean, low, high = interval([float(row[metric]) for row in group])
                summary.update({metric + "_mean": mean, metric + "_low": low, metric + "_high": high})
            summaries.append(summary)
        write_csv(output / "runs.csv", rows)
        write_csv(output / "summary.csv", summaries)
        if plots:
            plot(experiment, summaries, trajectories, output)
        write_report(experiment, summaries, manifest, output)
        manifest["status"] = "complete"
    except Exception as exc:
        manifest.update(status="failed", error_type=type(exc).__name__)
        raise
    finally:
        manifest["artifacts_sha256"] = {str(p.relative_to(output)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
                                        for p in output.rglob("*") if p.is_file() and p.name != "manifest.json"}
        save()
    return summaries


def plot(experiment, summaries, trajectories, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    if experiment == "composition":
        # Plot intact workflows; ablation outcomes remain in tables and report.
        selected = [r for r in summaries if r["control"] == "intact"]
        x_key, line_key, metric = "provenance_retention", "authorization", "global_violation"
        ignored = {x_key, line_key, "control"}
        ylabel = "Global disclosure fraction"
    else:
        selected = summaries
        x_key, line_key, metric = "arrival_probability", "arm", "final_backlog"
        ignored = {x_key, line_key}
        ylabel = "Final queued review requests"
    # Facet all other varying config parameters to avoid confounded averaging.
    config_keys = asdict(ENGINES[experiment][0]())
    varying = [k for k in config_keys if k not in ignored and len({r[k] for r in selected}) > 1]
    groups = {}
    for row in selected:
        key = tuple((k, row[k]) for k in varying)
        groups.setdefault(key, []).append(row)
    for index, (key, group) in enumerate(groups.items()):
        fig, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
        for label in sorted({r[line_key] for r in group}):
            subset = sorted((r for r in group if r[line_key] == label), key=lambda r: r[x_key])
            x = [r[x_key] for r in subset]
            ax.plot(x, [r[metric + "_mean"] for r in subset], "o-", label=label)
            ax.fill_between(x, [r[metric + "_low"] for r in subset], [r[metric + "_high"] for r in subset], alpha=0.15)
            if len(x) == 1:
                mean = subset[0][metric + "_mean"]
                ax.errorbar(x, [mean], yerr=[[max(0, mean - subset[0][metric + "_low"])], [max(0, subset[0][metric + "_high"] - mean)]], fmt="none", capsize=4, color=ax.lines[-1].get_color())
        ax.set(xlabel=x_key.replace("_", " "), ylabel=ylabel,
               title=f"{experiment.title()}: " + (", ".join(f"{k}={v}" for k, v in key) or "scripted pilot") + "\nMeans and 95% run-bootstrap intervals")
        ax.legend()
        if experiment == "composition":
            ax.set_ylim(-0.03, 1.03)
        ax.grid(alpha=0.2)
        for extension in ("png", "svg"):
            fig.savefig(output / f"outcomes_{index}.{extension}", dpi=150)
        plt.close(fig)
    if experiment == "oversight":
        target = max(trajectories, key=lambda r: r["config"]["arrival_probability"])["config"]
        selected = [r for r in trajectories if all(r["config"][k] == v for k, v in target.items() if k != "arm")]
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
        for arm in sorted({r["config"]["arm"] for r in selected}):
            runs = [r for r in selected if r["config"]["arm"] == arm]
            for ax, field, label in zip(axes, ("backlog", "unsafe"), ("Queued review requests", "Cumulative unsafe answers")):
                ax.plot(range(target["ticks"]), [sum(r["series"][t][field] for r in runs) / len(runs) for t in range(target["ticks"])], label=arm)
                ax.set(xlabel="Tick", ylabel=label)
                ax.grid(alpha=0.2)
        axes[0].legend()
        fig.suptitle(f"Oversight pilot: arrival probability={target['arrival_probability']}; means across seeds")
        for extension in ("png", "svg"):
            fig.savefig(output / f"trajectories.{extension}", dpi=150)
        plt.close(fig)


def write_report(experiment, summaries, manifest, output):
    shown = {"control", "authorization", "relays", "provenance_retention"} if experiment == "composition" else {"arm", "arrival_probability", "review_capacity", "capacity_scaling"}
    context_keys = [key for key in asdict(ENGINES[experiment][0]()) if key not in shown and len({row[key] for row in summaries}) > 1]
    treatment = lambda row: "; ".join(f"{key}={row[key]}" for key in context_keys) or "fixed"
    lines = [f"# {experiment.title()} scripted pilot", "", f"Completed {manifest['completed_runs']} runs. No LLM or external tool calls.", "",
             "These are finite synthetic experiments under explicit rules, not validated LLM behavior or evidence of phase transitions. Intervals use 1,000 run-level bootstrap resamples; repeated seeds are paired across treatments, not extra independent evidence.", ""]
    lines += ["Interpretation: workflow gates, retries, deadlines and reviewer behavior are programmed mechanisms. The tables describe synthetic outcomes under those rules; empirical agent validation remains pending.", ""]
    if experiment == "composition":
        lines += ["| Treatment | Control | Authorization | Relays | Retention | Disclosure mean | Authorized completion | 95% interval |", "|---|---|---|---:|---:|---:|---:|---|"]
        for r in summaries:
            lines.append(f"| {treatment(r)} | {r['control']} | {r['authorization']} | {r['relays']} | {r['provenance_retention']} | {r['global_violation_mean']:.3f} | {r['authorized_task_completion_mean']:.3f} | [{r['global_violation_low']:.3f}, {r['global_violation_high']:.3f}] |")
        lines += ["", "Minimum violating coalitions and leave-one-out controls are evaluated against each configured scripted workflow and its publication predicate, not for arbitrary agent organizations. Visible labels can be dropped while the environment retains true ancestry. The lineage gate conservatively blocks restricted descendants, including sanitized descendants; redaction is not implicit declassification."]
    else:
        lines += ["| Treatment | Arm | Arrival probability | Capacity | Scaling | rho_0 | Unsafe fraction | Final backlog | Pending tasks |", "|---|---|---:|---:|---|---|---:|---:|---:|"]
        for r in summaries:
            lines.append(f"| {treatment(r)} | {r['arm']} | {r['arrival_probability']} | {r['review_capacity']} | {r['capacity_scaling']} | {r['rho_0'] if r['rho_0'] is not None else r['rho_0_status']} | {r['unsafe_fraction_mean']:.3f} | {r['final_backlog_mean']:.2f} | {r['pending_at_horizon_mean']:.2f} |")
        lines += ["", "Original offered load excludes retry demand and estimation errors. Original requests, retry demand, stale requests and unique pending tasks are separate columns in the CSV outputs. Backlog includes stale duplicate review requests; pending tasks are distinct unresolved jobs. Completed-review delay excludes unresolved/abandoned jobs and is not an unbiased estimate of all-job waiting time. Arrivals continue through the last tick; no drain period is applied. Retry feedback is imposed, not inferred as an emergent LLM strategy. Unbounded review still respects configured latency."]
    lines += ["", "Full configurations and bootstrap intervals: summary.csv. Seed-level outcomes: runs.csv. Parent-linked traces: runs/*.events.jsonl.gz. See the experiment protocol under docs/ for update order, denominators and limitations."]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", choices=ENGINES)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()
    config = args.config or Path(f"configs/{args.experiment}_small.json")
    output = args.output or Path(f"results/local-{args.experiment}")
    try:
        summaries = run_sweep(args.experiment, json.loads(config.read_text(encoding="utf-8")), output, plots=not args.no_plots)
    except (ValueError, TypeError, KeyError, ImportError) as exc:
        parser.exit(2, f"Experiment failed: {exc}\n")
    print(f"Completed {len(summaries)} configurations: {output.resolve()}")


if __name__ == "__main__":
    main()
