"""Reproducible Cartesian sweeps, run-level bootstrap intervals and artifacts."""
import argparse
import csv
from dataclasses import asdict
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys

from . import __version__
from .model import ARMS, Config, canonical, simulate

METRICS = ("affected_fraction", "final_active_fraction", "wrong_answer_fraction", "recurrence_count", "max_backlog", "right_censored")


def interval(values, seed=0, repetitions=1000):
    rng = random.Random(seed)
    samples = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(repetitions))
    return statistics.mean(values), samples[int(0.025 * repetitions)], samples[int(0.975 * repetitions)]


def expand(spec):
    if set(spec) - {"base", "axes", "seeds"}:
        raise ValueError("unknown sweep fields")
    seeds = spec["seeds"]
    if not seeds or len(set(seeds)) != len(seeds) or any(type(s) is not int or s < 0 for s in seeds):
        raise ValueError("seeds must be unique nonnegative integers")
    axes = spec.get("axes", {})
    if any(not values or len({canonical(v) for v in values}) != len(values) for values in axes.values()):
        raise ValueError("axes must be nonempty and contain unique values")
    names = sorted(axes)
    configs = [Config(**(spec.get("base", {}) | dict(zip(names, values)))) for values in itertools.product(*(axes[n] for n in names))]
    return configs, seeds


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def provenance():
    root = Path(__file__).resolve().parent.parent
    hashes = {str(p.relative_to(root)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
              for folder in ("mas_failure_lab", "tests", "configs") for p in sorted((root / folder).rglob("*"))
              if p.is_file() and "__pycache__" not in p.parts}
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, stderr=subprocess.DEVNULL, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        revision, dirty = None, None
    return dict(version=__version__, python=sys.version, platform=platform.platform(), git_revision=revision,
                git_dirty=dirty, source_sha256=hashes, random_scheme="sha256-keyed-v1", bootstrap_repetitions=1000)


def run_sweep(spec, output: Path, *, plots=True):
    configs, seeds = expand(spec)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    (output / "runs").mkdir()
    manifest = provenance() | {"sweep": spec, "run_count": len(configs) * len(seeds), "status": "running"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    rows, summary, trajectories = [], [], []
    for config in configs:
        group = []
        for seed in seeds:
            result = simulate(config, seed)
            path = output / "runs" / result["run_id"]
            # mtime=0 and empty gzip filename make log bytes reproducible too.
            with path.with_suffix(".events.jsonl.gz").open("wb") as raw:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
                    for event in result.pop("events"):
                        stream.write((canonical(event) + "\n").encode())
            path.with_suffix(".json").write_text(canonical(result) + "\n", encoding="utf-8")
            metrics = {k: v for k, v in result["metrics"].items() if k != "attributable_offspring"}
            rows.append({"run_id": result["run_id"], "seed": seed, **asdict(config), **metrics})
            group.append(result["metrics"])
            trajectories.append(result)
        aggregated = asdict(config) | {"replicates": len(seeds)}
        for metric in METRICS:
            mean, low, high = interval([float(r[metric]) for r in group])
            aggregated.update({metric + "_mean": mean, metric + "_low": low, metric + "_high": high})
        summary.append(aggregated)
    write_csv(output / "runs.csv", rows)
    write_csv(output / "summary.csv", summary)
    contrasts = []
    # Paired effect of longest vs shortest artifact TTL for each other config.
    ttls = sorted({c.memory_ttl for c in configs})
    if len(ttls) > 1:
        buckets = {}
        for row in rows:
            if row["arm"] == "cascade" and row["memory_ttl"] in (ttls[0], ttls[-1]):
                key = canonical({k: row[k] for k in asdict(configs[0]) if k != "memory_ttl"})
                buckets.setdefault(key, {}).setdefault(row["seed"], {})[row["memory_ttl"]] = row
        for key, pairs in buckets.items():
            if not all(set(pair) == {ttls[0], ttls[-1]} for pair in pairs.values()):
                continue
            for metric in ("affected_fraction", "final_active_fraction", "recurrence_count"):
                values = [pair[ttls[-1]][metric] - pair[ttls[0]][metric] for pair in pairs.values()]
                mean, low, high = interval(values)
                contrasts.append(json.loads(key) | dict(metric=metric, ttl_low=ttls[0], ttl_high=ttls[-1], difference=mean, low=low, high=high))
    if contrasts:
        write_csv(output / "paired_contrasts.csv", contrasts)
    if plots:
        plot(output, summary, trajectories)
    report(output, summary, contrasts, manifest)
    manifest["status"] = "complete"
    manifest["artifacts_sha256"] = {str(p.relative_to(output)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in sorted(output.rglob("*")) if p.is_file() and p.name != "manifest.json"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return summary


def plot(output, summary, runs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # Facet every non-x, non-arm changing parameter; do not pool unrelated treatments.
    varying = [k for k in asdict(Config()) if k not in ("cross_probability", "arm") and len({r[k] for r in summary}) > 1]
    groups = {}
    for row in summary:
        key = tuple((k, row[k]) for k in varying)
        groups.setdefault(key, []).append(row)
    for index, (key, group) in enumerate(groups.items()):
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
        for ax, metric, label in zip(axes, ("affected_fraction", "final_active_fraction"), ("Ever affected fraction", "Final active fraction")):
            for arm in ARMS:
                selected = sorted((r for r in group if r["arm"] == arm), key=lambda r: r["cross_probability"])
                if not selected:
                    continue
                x = [r["cross_probability"] for r in selected]
                y = [r[metric + "_mean"] for r in selected]
                ax.plot(x, y, "o-", label=arm)
                ax.fill_between(x, [r[metric + "_low"] for r in selected], [r[metric + "_high"] for r in selected], alpha=0.12)
            ax.set(xlabel="Cross-team edge probability (cascade arm)", ylabel=label, ylim=(-0.03, 1.03))
            ax.grid(alpha=0.2)
        axes[0].legend(fontsize=8)
        fig.suptitle("Experiment 1: " + (", ".join(f"{k}={v}" for k, v in key) or "pilot") + "\nMeans and 95% run-bootstrap intervals; no phase-transition inference", fontsize=11)
        for ext in ("png", "svg"):
            fig.savefig(output / f"regimes_{index}.{ext}", dpi=160)
        plt.close(fig)
    # A fixed config (highest cross probability/TTL), averaged over independent runs.
    target = max((r for r in runs if r["config"]["arm"] == "cascade"), key=lambda r: (r["config"]["cross_probability"], r["config"]["memory_ttl"]), default=runs[0])
    chosen = [r for r in runs if r["config"] == target["config"]]
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    ticks = [s["tick"] for s in target["series"]]
    for run in chosen:
        ax.plot(ticks, [s["active"] / run["config"]["n"] for s in run["series"]], color="#3174ad", alpha=0.18)
    ax.plot(ticks, [statistics.mean(r["series"][t]["active"] / r["config"]["n"] for r in chosen) for t in ticks], color="#143b59", label="Run mean", linewidth=2)
    ax.set(xlabel="Tick", ylabel="Active deviation fraction", ylim=(-0.03, 1.03), title=f"{target['config']['arm']}: cross={target['config']['cross_probability']}, TTL={target['config']['memory_ttl']}\nIndividual seeded trajectories and mean")
    ax.legend()
    fig.savefig(output / "trajectories.png", dpi=160)
    fig.savefig(output / "trajectories.svg")
    plt.close(fig)


def report(output, summary, contrasts, manifest):
    lines = ["# Experiment 1 pilot", "", f"Completed {manifest['run_count']} scripted simulations. No LLM calls were made.", "",
             "Intervals are percentile bootstrap intervals over runs (1,000 resamples); small samples and boundary outcomes can produce misleadingly narrow intervals. These are descriptive, unadjusted pilot comparisons.", "",
             "| Arm | Cross probability | Artifact TTL | Ever affected mean | Final active mean | Unresolved at horizon |", "|---|---:|---:|---:|---:|---:|"]
    for row in summary:
        lines.append(f"| {row['arm']} | {row['cross_probability']} | {row['memory_ttl']} | {row['affected_fraction_mean']:.3f} | {row['final_active_fraction_mean']:.3f} | {row['right_censored_mean']:.3f} |")
    lines += ["", "Full configurations and intervals are in summary.csv; seed-level outcomes are in runs.csv.", "", "## Paired artifact-persistence contrasts", "", "Same seeds, graph draws, scheduler and decision draws; differences are longest TTL minus shortest TTL. Controls have both endogenous channels disabled, so their cross/TTL duplicates are deliberate invariance checks.", "", "| Cross probability | Metric | Difference | 95% interval |", "|---:|---|---:|---|"]
    for c in contrasts:
        lines.append(f"| {c['cross_probability']} | {c['metric']} | {c['difference']:.3f} | [{c['low']:.3f}, {c['high']:.3f}] |")
    lines += ["", "## Interpretation limits", "", "These outcomes describe finite-horizon failure regimes under imposed rules. They do not establish a phase transition, criticality, real-world agent escape rates, or LLM behavior. Artifact persistence and recovery are model assumptions. Extinction is right-censored when active deviations or contaminated memory remain. Common-cause and independent arms have matched marginal exposure probabilities but different dependence; they are not exposure-count-matched to the single-seed arms.", "", "A phase-transition claim would need a size series, longer horizons, finite-size analysis, alternative transition rules and nulls. Independent restarts in this Cartesian sweep are not a hysteresis experiment. LLM calibration, held-out topologies and stronger statistical power remain future work."]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/small.json"))
    parser.add_argument("--output", type=Path, default=Path("results/local"))
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()
    try:
        summary = run_sweep(json.loads(args.config.read_text(encoding="utf-8")), args.output, plots=not args.no_plots)
    except (ValueError, TypeError, KeyError, ImportError) as exc:
        parser.exit(2, f"Experiment failed: {exc}\n")
    print(f"Completed {len(summary)} configurations. Results: {args.output.resolve()}")


if __name__ == "__main__":
    main()
