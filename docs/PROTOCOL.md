# Experiment 1 protocol, version 0.1

## Question and estimands

Under explicit stochastic rules, how do cross-team communication and persistent team artifacts change reach, recurrence and residual deviation at a fixed horizon?

Primary outcomes: ever-affected agent fraction (including exogenous seeds), final active fraction, and recurrence count (episodes after the first per agent). Secondary outcomes: peak prevalence, wrong-answer fraction over executed decisions, active-agent ticks excluding initial tick 0, review backlog, last active tick, model-attributed offspring, and extinction time with a right-censor flag. An affected agent has held the unsupported claim, even if corrected before producing an answer. Active prevalence and executed-answer error rate are different denominators.

The pilot reports paired longest-minus-shortest TTL contrasts at each cross probability and all configuration means. Graph/scheduling/decision draws are paired by seed and semantic key. Adding cross edges can displace contacts under a fixed contact budget, so larger cross probability need not monotonically increase reach. Paired seeds reduce noise but do not guarantee monotone counterfactuals.

## Explicit assumptions

1. One correct synthetic fact (7 samples) and one unsupported claim (9) replace general language. Verification reads D0 and is perfect. Initially all agents hold truth except exogenous perturbations.
2. Graphs are undirected, static, simple, and can be disconnected. Modular graphs draw within-team and cross-team edges separately. Teams are contiguous agent ID blocks; the last team may be smaller. Ring/complete topologies ignore edge probabilities.
3. Each scheduled agent samples up to `contacts` distinct neighbors, uniformly by keyed priorities. This is an incoming observation budget. Only incorrect peer claims enter the adoption candidates; true messages alone do not correct an agent. Thus the baseline intentionally models asymmetric contamination; alternate truth-propagation rules are future robustness checks.
4. Scripted agents first verify with probability v. Otherwise they adopt with probability a, selecting uniformly among available incorrect exposures. Multiple exposure paths are candidates, not independent infection attempts. A deviation persists until verification, scheduled recovery or intervention; re-exposure while already deviating does not reset its recovery clock.
5. Each team has one last-writer-wins artifact slot. All scheduled deviating agents publish at the end of a tick; highest agent ID wins. Writes refresh the TTL; reads do not. A write at tick t with TTL L expires before reads at t+L (so TTL 1 has no future read opportunity). TTL 0 disables memory. No global shared-memory pool or artifact cleaning is modeled. Writes are a bundled effect of a decision, not separately budgeted tool calls.
6. Recovery occurs after a fixed number of ticks from episode onset. Monitoring detects every deviation at the end of a tick; false positives and missed detections are absent. Due reviews are serviced oldest-due first, with agent ID tie-breaking. Corrections do not clear team memory. The monitor is an idealized authority, not another language agent.
7. `monitor_capacity` is the number of interventions per tick. Proportional mode multiplies it by ceil(n/team_size). Capacity and latency act independently. Enqueueing at tick t is after processing, so earliest service is t+max(1, latency); latency 0 still takes one tick. Initial seeds enter the review queue at the end of tick 1, if still active. Stale episode reviews are cancelled or replaced, never applied to a new episode.
8. One decision is the compute unit. Per-agent mode schedules all n agents each tick. Fixed mode schedules min(n, compute_budget) agents by independent keyed priorities; unscheduled agents may still recover and be monitored. Contacts and task submissions scale with scheduled decisions. No token-cost equivalence is claimed.
9. One-shot seeds/exposures occur only at tick 0. There is no spontaneous background error thereafter. Recovery can therefore reach an absorbing clean state when both agents and artifacts are clean. No environment escape, real secrets, tool execution, or malicious payload is present.

These assumptions can manufacture or suppress persistence. Results are properties of this model until calibrated and tested against actual agents.

## Update order

Tick 0: create graph/document; force the assigned exogenous deviations; log initial state.

Each later tick:

1. Expire memory; service eligible reviews within capacity; perform scheduled recovery.
2. Freeze agent states. Select agents and contacts; deliver peer messages and previous-tick memory reads; collect decisions without applying them.
3. Apply verification/adoption; produce and check structured answers.
4. Publish contaminated artifacts; enqueue active episodes; log state/backlog.

An adoption cannot propagate through two edges within one tick. A corrected agent may be reinfected later that same tick by prior memory or another agent. Simulation runs for the full horizon even after extinction so controls have equal observation windows.

## Controls and causal interpretation

| Arm | Tick-0 intervention | Communication | Endogenous memory |
|---|---|---|---|
| cascade | Force agent 0 to hold the false claim | Enabled | Enabled if TTL > 0 |
| isolated_seed | Same seed as cascade | Disabled | Disabled |
| independent | Independent Bernoulli(q) exposure per agent, unique root per error | Disabled | Disabled |
| common_cause | One Bernoulli(q) shock, exposing everyone if it occurs | Disabled | Disabled |

Independent and common-cause arms have the same per-agent marginal exposure q and expected initial count n*q. At the pilot's q=1/16, expected count is one, but realized counts differ from the exactly-one seeded arms. Common exposure is delivered by a shared root event, not endogenous memory. Its extreme all-or-none dependence is a chosen null model. With 20 replicates, rare shared shocks are poorly estimated; zero observed shocks would not imply zero risk. Hold q fixed for marginal-risk comparisons or explicitly set q=1/n to match expected initial count in size studies.

Cascade vs isolated_seed estimates the combined effect of both endogenous channels. Within cascade, TTL 0 versus positive TTL ablates artifacts while retaining communication. `contacts=0` with positive TTL isolates team memory. `verification=1`, `adoption=0`, and zero-exposure independent runs provide limiting-case checks. Cross-team link effects are conditional on contact competition and the chosen graph construction. Provenance identifies the model-selected transmission parent; it is not an empirical causal-effect estimate when multiple exposures could have sufficed.

## Uncertainty, reproducibility and claims

Each seed is the inferential unit. Bootstrap means and paired differences use 1,000 run-level resamples and percentile 95% intervals; no independence is assumed among agents or ticks. Intervals are descriptive, not multiplicity-adjusted hypothesis tests. Degenerate intervals at boundaries are especially unreliable at small n_runs. Do not pool repeated control configurations as extra evidence.

Extinction requires no active deviations and no live contaminated memory at the horizon; its reported tick is the beginning of the final clean suffix, including artifact expiry. Otherwise extinction time is null and right_censored is true. Last active tick is a separate finite-horizon observation. Do not treat censored runs as recovered at the horizon or estimate mean recovery from only successful runs.

Event logs use sequential IDs, causal parent links, exogenous root IDs and run IDs. Config + seed + agent metadata determine the run ID, so compare source fingerprints before treating identical IDs from different code versions as identical experiments. The manifest records source hashes, interpreter/platform, optional Git revision/dirty status, normalized sweep inputs, and output checksums. Random draws use SHA-256 keys, avoiding dependence on loop order or Python's salted hash. Simulation JSON/CSV/gzip replay is deterministic for the same code/config/runtime. Matplotlib SVG/PDF metadata and platform font rendering need not be byte-identical.

State changes are individual episodes. Different reach/persistence patterns may be described as finite-horizon failure regimes. The small sweep does not establish a sharp regime boundary, a thermodynamic limit, a phase transition, criticality, heavy tails, hysteresis, or early-warning validity. Those claims need pre-specified size/horizon series, alternative rules, null comparisons, distributional diagnostics and held-out empirical validation. No claims in the motivating conversation about contemporary incidents or prior literature are independently evaluated by this implementation.
