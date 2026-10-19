# Oversight scripted pilot

Completed 192 runs. No LLM or external tool calls.

These are finite synthetic experiments under explicit rules, not validated LLM behavior or evidence of phase transitions. Intervals use 1,000 run-level bootstrap resamples; repeated seeds are paired across treatments, not extra independent evidence.

| Arm | Arrival probability | Capacity | Scaling | Unsafe fraction | Final backlog | Pending tasks |
|---|---:|---:|---|---:|---:|---:|
| feedback | 0.1 | 2 | fixed | 0.000 | 0.83 | 0.83 |
| feedback | 0.3 | 2 | fixed | 0.039 | 22.08 | 6.58 |
| feedback | 0.6 | 2 | fixed | 0.268 | 217.42 | 20.25 |
| feedback | 0.9 | 2 | fixed | 0.309 | 374.42 | 30.25 |
| no_retries | 0.1 | 2 | fixed | 0.000 | 0.83 | 0.83 |
| no_retries | 0.3 | 2 | fixed | 0.000 | 3.67 | 3.67 |
| no_retries | 0.6 | 2 | fixed | 0.225 | 44.75 | 20.25 |
| no_retries | 0.9 | 2 | fixed | 0.296 | 98.83 | 30.25 |
| deduplicated | 0.1 | 2 | fixed | 0.000 | 0.83 | 0.83 |
| deduplicated | 0.3 | 2 | fixed | 0.000 | 3.67 | 3.67 |
| deduplicated | 0.6 | 2 | fixed | 0.225 | 44.75 | 20.25 |
| deduplicated | 0.9 | 2 | fixed | 0.296 | 98.83 | 30.25 |
| unbounded | 0.1 | 2 | fixed | 0.000 | 0.75 | 0.75 |
| unbounded | 0.3 | 2 | fixed | 0.000 | 2.00 | 2.00 |
| unbounded | 0.6 | 2 | fixed | 0.000 | 3.75 | 3.75 |
| unbounded | 0.9 | 2 | fixed | 0.000 | 5.33 | 5.33 |

Backlog includes stale duplicate review requests; pending tasks are distinct unresolved jobs. Completed-review delay excludes unresolved/abandoned jobs and is not an unbiased estimate of all-job waiting time. Arrivals continue through the last tick; no drain period is applied. Retry feedback is imposed, not inferred as an emergent LLM strategy. Unbounded review still respects configured latency.

Full configurations and bootstrap intervals: summary.csv. Seed-level outcomes: runs.csv. Parent-linked traces: runs/*.events.jsonl.gz. See the experiment protocol under docs/ for update order, denominators and limitations.
