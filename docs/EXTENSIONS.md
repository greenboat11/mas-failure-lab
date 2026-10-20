# Extension treatments and reproducibility

## Compatibility contract

Old public commands and default mechanism settings use `sha256-keyed-v1`. With all extension fields at their defaults, the serialized configuration omits those fields: run IDs, states, metrics and event sequences replay the historical pilots exactly. The test suite checks one saved run per original arm/control and every historical artifact checksum. No historical output or fingerprint is rewritten.

`split-v2` uses independent seed domains. `topology_seed` controls graph keys; `task_seed` controls exogenous exposure, arrivals and difficulty; `policy_seed` controls scheduling, contacts, verification, retention, review estimates, review quality and choices. Missing explicit seeds resolve to the run's base seed. Fixing a domain seed across base seeds intentionally repeats that domain; do not count repeated environments as independent samples. `trial_id` changes run identity without changing environment draws. Scripted trial variation requires varying policy_seed, whereas repeated LLM samples may vary despite identical settings. Runner manifests record resolved seed plans.

Shared serialization, randomness, events, statistics, source provenance and run writers live in dedicated modules. Original import locations re-export compatibility helpers. State meanings remain experiment-specific. New reports add derived diagnostics; raw legacy engine replay retains its historical schema.

## Experiment 1

`baseline=asymmetric_contamination` is the preserved default. For `baseline=corrective`, three independent probabilities can be enabled:

- `corrective_peer`: a true peer message becomes an adoption candidate for a currently deviating recipient. It competes with false exposures under the same candidate-selection rule.
- `corrective_write`: a currently correct scheduled agent may write truth into the team slot. Sorted agent-ID last-writer-wins ordering remains in effect; a later false write can overwrite a correction, or vice versa.
- `artifact_cleanup`: remove an unexpired contaminated artifact before interventions/observations on that tick. This is a per-artifact probability and idealized detection assumption, independent of monitor capacity.

Correct artifacts can correct deviating readers. TTL applies to both values. Extinction requires no active deviations or contaminated artifacts; clean artifacts do not prevent extinction. The corrected mode tracks contaminated artifact counts in snapshots. Zero probabilities reproduce the same asymmetric mechanisms while retaining explicit treatment identity.

### Matched scaling treatments

`configs/scaling_matched.json` uses an Erdos-Renyi communication graph to make the controlled quantities explicit:

| Treatment | Held fixed as N varies | Changes that remain |
|---|---|---|
| `edge_probability` | Pairwise p=`cross_probability` | Expected degree (N-1)p and potential total contacts grow |
| `expected_degree` | k=`expected_degree`, using p=k/(N-1) | Components, density and realized degree fluctuate; total scheduled contacts can grow |
| `communication_budget` | Total selected directed peer observations per tick <=B | Per-agent average opportunities shrink; underlying graph still uses fixed p |

In all three, `contacts` caps distinct neighbors sampled per scheduled agent. The total-budget treatment samples among eligible directed observations by keyed priority; it does not force messages when graphs or compute scheduling provide fewer than B. Task/decision counts remain governed by compute_scaling, not communication_budget. These are three distinct interventions, not a design that holds all three quantities fixed simultaneously.

New run/summary CSVs report realized edges, density, mean/max degree, isolated vertices, connected components and executed message totals. Fixed expected degree is an ensemble expectation, not exact regular degree in each graph. Fixed/proportional monitoring and compute budgets remain independent design choices.

## Experiment 2

`workflow_mode=fixed` preserves the original workflow and analytical benchmark. Set `report_completion=true` to add completion to a direct fixed-engine result; new sweep reports derive it automatically. For the legacy task, a published sanitized marker counts as the authorized result; simply blocking publication does not.

`workflow_mode=alternatives` assembles complementary inputs, one/two transform actors, optional transform-specific relay chains, one/two publishers, and optional relay bypasses. Every eligible configured route is evaluated. Removal controls affect the first actor/path only, allowing redundant routes to survive. Exact subset enumeration uses route presence and the actual authorization predicate, with at most ten actors. It can find smaller violating coalitions than total role count. Audit draws are keyed by actor, so a shared actor has the same retention outcome across alternative routes; route events are not independent Bernoulli trials.

`sanitizing_routes` makes the first transforms produce only the specified public summary. Other transforms append the canary. `global_policy` authorization checks the exact synthetic canary predicate and allows a public summary; `lineage` blocks all restricted descendants, including sanitized ones. This comparison isolates useful authorized work from conservative blocking. The idealized content predicate is not a semantic detector for real data.

The alternative workflow reports configured_agents separately from participating_agents; participation counts unique actors with recorded reads, transforms, handoffs or publication attempts, excluding configuration-only roles and decision-only actors.

Task completion means some permitted output was published. Authorized task completion requires a public summary without the canary. A run may have both an authorized output and a separate disclosure through another route. Coalition audits optimize the existence of disclosure, not utility or the number of routes. Repeated calls to an actor across routes are bundled workflow evaluations, not measured compute usage. The fixed analytical formula does not apply to redundant routes.

## Experiment 3

`baseline=oracle` preserves perfect review-need observations, perfect review and environment-driven retry timing. The extended mode adds sensitivity/specificity of a binary review-need estimate. Agents see the estimate; the environment retains true difficulty. False positives add original queue demand; false negatives can lead to immediate unsafe answers. The nominal rho_0 still uses true original hard-task demand, so realized escalation may differ.

`retry_mode=agent` calls the policy at each permitted retry opportunity. It sees elapsed waiting and prior attempts and chooses retry or wait. The scripted extension uses retry_probability; timing opportunities and deadlines remain imposed rules. The no_retries arm disables these opportunities and deduplicated suppresses duplicate submissions. `review_accuracy` is the probability of a correct review on a hard task; errors can produce unsafe reviewed outcomes. This model does not corrupt easy answers during review.

New outputs separate original review requests, retry attempts, enqueued retry demand, suppressed retries, live/stale queued requests, unique pending tasks and review errors. Request conservation is final_backlog=original_review_demand+retry_demand-serviced, with no cancellations. Task conservation remains arrivals=answered+reviewed+abstained+pending; reviewed includes erroneous reviews, and unsafe is an overlapping outcome count.

rho_0 is nominal hard-task arrivals per tick divided by effective service capacity. Finite zero capacity uses null with `infinite` or `undefined_zero_over_zero`; unlimited service uses rho_0=0 with `unbounded_service`, retaining the configured finite capacity separately. These diagnostics do not assert stationarity, queue stability or a phase transition.
