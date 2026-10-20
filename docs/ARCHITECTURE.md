# Framework layout and extension contracts

| Layer | Location | Responsibility |
|---|---|---|
| Experiment 1 | `model.py`, `agents.py`, `experiment.py` | Claim dynamics, structured evidence choices, established sweep CLI |
| Experiment 2 | `composition.py` | Complementary capability workflow, canary checks, coalition audits |
| Experiment 3 | `oversight.py` | Task arrivals, review queue, retries, deadlines |
| Shared support | `common.py`, `suite.py`, utilities in `experiment.py` | Event envelopes, action-policy boundary, sweep outputs, intervals, provenance |
| Shared primitives | `events.py`, `randomness.py`, `statistics.py`, `serialization.py`, `provenance.py`, `runner.py` | Versioned keys, compatibility records, event envelopes and artifact writing |
| Bounded retrieval | `retrieval.py` | Priced evidence access, language claims, truth checks, repeated trials and offline replay |
| LLM preparation | `providers.py`, `llm_pilot.py` | Audited optional Responses transport, exact offline replay, opt-in paid execution |
| Research configuration | `configs/`, `docs/` | Explicit treatments, controls, assumptions and roadmap |

The engines remain separate because an infection state, a composed artifact and a queued task have different semantics. Experiment 1's existing CLI and schema are preserved. Experiments 2 and 3 share an action-policy protocol (`metadata`, `choose(observation, draw)`) with experiment-specific allowed actions. Their scripted policies are runnable now; the OpenAI structured-response adapter currently targets Experiment 1 only. Do not route the same verify/adopt schema into the other experiments.

All engines use keyed deterministic random draws and sequential parent-linked event IDs. In Experiment 1, roots denote perturbations. In Experiment 2, roots denote restricted synthetic inputs. In Experiment 3, roots denote arriving tasks. Do not treat all roots as errors. Parent links track modeled provenance, not automatically identified empirical causal effects.

The public event envelope is schema version 1. New engines identify themselves and engine_version=1 in `run_started`, use source fingerprints in the manifest, and include their policy in run identity. Original pilot artifacts retain the original source fingerprints; comparing those against newer source is expected to show changes. Treat bundled runs as versioned historical artifacts, not as claims that every old file was regenerated on the latest source.

Every sweep writes a manifest, per-run JSON and deterministic gzip logs, seed-level CSV, configuration summaries, a report and optional PNG/SVG plots. Output directories must be empty. New-engine runners preserve a failed manifest and completed artifacts on an exception. No automatic remote calls, paid tests, publication, or hidden retries occur during default commands or CI.

To add a treatment: define and validate a config field, identify which transitions it changes, add limiting-case and matched-control tests, update the protocol, run a small pilot, inspect plots and record source fingerprints. To add a provider: preserve the per-experiment action schema and environment-owned outcomes; log actual requests, responses, usage and provider versions. Never label a fake provider's outputs as real LLM observations.
