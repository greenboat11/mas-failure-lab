# Event schema v1

Each run produces `<run_id>.events.jsonl.gz` and `<run_id>.json`. The latter contains full configuration, seed, agent metadata, relationship layers, time series and metrics. Decompress logs with Python's `gzip.open(path, 'rt')`.

Every event has `schema_version`, `run_id`, `event_id`, `tick`, `kind`, `actor`, `parents` and `roots`, plus kind-specific data. IDs are positions in the log; parent IDs always point backward. Root perturbations list themselves in `roots`. True evidence has no perturbation roots. Roots describe contamination ancestry, not all administrative dependencies.

Typical lineage:

```text
seed_perturbation -> deviation -> message -> deviation -> answer
                             -> artifact_write -> artifact_read -> deviation
```

The deviation's parent is the chosen observation, while its corresponding decision event records every candidate, draws and the returned action. An answer references both its current source and decision. Verification/intervention/recovery references the corrected episode and truth document. Repeated exposures without a new episode are visible in observations and messages; they do not create an extra deviation event.

Other kinds: `run_started`, `document`, `shared_shock`, `independent_error`, `artifact_expired`, `review_enqueued`, `review_cancelled`, `snapshot`. Actor may be null for environment events. Communication messages record recipient and integer value; artifacts record team and expiry. Answers contain `sample_count` and source event citations. The `correct` field is computed by the environment from its owned state; an agent cannot set it.

`attributable_offspring` maps parent deviation event IDs to counts of directly selected downstream acquisition events, walking through message/artifact wrapper events. It excludes initial exogenous episodes, counts reinfections as episodes, and is not a basic reproduction-number estimate. Summing it gives total modeled adoption episodes.

Decision events preserve the normalized observation and structured result. Provider metadata belongs in the run metadata; raw vendor responses, usage/cost and retry traces are not yet captured. Extend the adapter and schema before treating real-provider runs as fully audited LLM experiments.
