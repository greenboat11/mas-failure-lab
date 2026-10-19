# Experiment 1 pilot

Completed 480 scripted simulations. No LLM calls were made.

Intervals are percentile bootstrap intervals over runs (1,000 resamples); small samples and boundary outcomes can produce misleadingly narrow intervals. These are descriptive, unadjusted pilot comparisons.

| Arm | Cross probability | Artifact TTL | Ever affected mean | Final active mean | Unresolved at horizon |
|---|---:|---:|---:|---:|---:|
| cascade | 0.0 | 0 | 0.212 | 0.009 | 0.050 |
| cascade | 0.0 | 6 | 0.250 | 0.159 | 1.000 |
| cascade | 0.08 | 0 | 0.541 | 0.284 | 0.450 |
| cascade | 0.08 | 6 | 0.938 | 0.669 | 1.000 |
| cascade | 0.3 | 0 | 0.675 | 0.434 | 0.650 |
| cascade | 0.3 | 6 | 1.000 | 0.713 | 1.000 |
| isolated_seed | 0.0 | 0 | 0.062 | 0.000 | 0.000 |
| isolated_seed | 0.0 | 6 | 0.062 | 0.000 | 0.000 |
| isolated_seed | 0.08 | 0 | 0.062 | 0.000 | 0.000 |
| isolated_seed | 0.08 | 6 | 0.062 | 0.000 | 0.000 |
| isolated_seed | 0.3 | 0 | 0.062 | 0.000 | 0.000 |
| isolated_seed | 0.3 | 6 | 0.062 | 0.000 | 0.000 |
| independent | 0.0 | 0 | 0.059 | 0.000 | 0.000 |
| independent | 0.0 | 6 | 0.059 | 0.000 | 0.000 |
| independent | 0.08 | 0 | 0.059 | 0.000 | 0.000 |
| independent | 0.08 | 6 | 0.059 | 0.000 | 0.000 |
| independent | 0.3 | 0 | 0.059 | 0.000 | 0.000 |
| independent | 0.3 | 6 | 0.059 | 0.000 | 0.000 |
| common_cause | 0.0 | 0 | 0.100 | 0.000 | 0.000 |
| common_cause | 0.0 | 6 | 0.100 | 0.000 | 0.000 |
| common_cause | 0.08 | 0 | 0.100 | 0.000 | 0.000 |
| common_cause | 0.08 | 6 | 0.100 | 0.000 | 0.000 |
| common_cause | 0.3 | 0 | 0.100 | 0.000 | 0.000 |
| common_cause | 0.3 | 6 | 0.100 | 0.000 | 0.000 |

Full configurations and intervals are in summary.csv; seed-level outcomes are in runs.csv.

## Paired artifact-persistence contrasts

Same seeds, graph draws, scheduler and decision draws; differences are longest TTL minus shortest TTL. Controls have both endogenous channels disabled, so their cross/TTL duplicates are deliberate invariance checks.

| Cross probability | Metric | Difference | 95% interval |
|---:|---|---:|---|
| 0.0 | affected_fraction | 0.037 | [0.016, 0.059] |
| 0.0 | final_active_fraction | 0.150 | [0.125, 0.175] |
| 0.0 | recurrence_count | 17.000 | [14.000, 19.800] |
| 0.08 | affected_fraction | 0.397 | [0.225, 0.566] |
| 0.08 | final_active_fraction | 0.384 | [0.234, 0.531] |
| 0.08 | recurrence_count | 27.300 | [18.050, 36.450] |
| 0.3 | affected_fraction | 0.325 | [0.141, 0.516] |
| 0.3 | final_active_fraction | 0.278 | [0.147, 0.425] |
| 0.3 | recurrence_count | 22.750 | [13.000, 33.550] |

## Interpretation limits

These outcomes describe finite-horizon failure regimes under imposed rules. They do not establish a phase transition, criticality, real-world agent escape rates, or LLM behavior. Artifact persistence and recovery are model assumptions. Extinction is right-censored when active deviations or contaminated memory remain. Common-cause and independent arms have matched marginal exposure probabilities but different dependence; they are not exposure-count-matched to the single-seed arms.

A phase-transition claim would need a size series, longer horizons, finite-size analysis, alternative transition rules and nulls. Independent restarts in this Cartesian sweep are not a hysteresis experiment. LLM calibration, held-out topologies and stronger statistical power remain future work.
