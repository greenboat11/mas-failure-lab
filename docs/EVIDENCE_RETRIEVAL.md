# Bounded evidence retrieval and later LLM validation

The restricted-choice integration task remains available through `python -m mas_failure_lab.llm_pilot`. The new task is `python -m mas_failure_lab.retrieval`, an offline/mock-only CLI. Its provider-neutral `EvidenceTransportAgent` prepares another action schema; it supplies no paid transport. Real model execution still requires a separately specified provider/model, settings and budget.

## Task and observations

A synthetic official register contains a station sample count. A clearly labeled unverified working note contains a different count. Initial observations expose the task, document titles/IDs, remaining turns/credits and natural-language peer claims, but not document contents or the environment's ground truth. An initial unsupported peer claim is an optional perturbation. Communication and seeded claims can be independently disabled.

Each agent has at most `turns` actions. It may retrieve one named document, answer with an integer plus citations and a short natural-language message, or abstain. Each retrieval spends retrieval_cost credits; exhausted budgets are enforced by the environment. Retrieved documents remain visible on subsequent turns. Retrieval is the only way to access the official text. Messages from completed answers become available to other agents on the next turn; the environment uses a complete communication network here. This is language evidence exchange, not unrestricted autonomous tool use.

Scoring is +1 per correct answer, -1 per wrong answer, zero for abstention, minus credits_spent*utility_cost_per_credit. Credit constraints and utility costs are different: the former limits access, the latter exposes a tradeoff. A model can choose not to retrieve. A last-turn retrieval may leave an agent unfinished; these are reported separately from abstentions and answers.

Truth checks are environment-owned. Factual correctness and authoritative support are separate: a lucky/copy answer can be correct without citing an accessed official document. Fabricated or inaccessible citations are rejected. Peer text is unconstrained within a 500-character limit, but answers are structured. The environment evaluates the structured answer value, not semantic consistency of every sentence in peer prose; that limitation must be addressed before language-level claims.

## Trials, auditing and replay

`configs/retrieval_mock.json` repeats three trial IDs on the same environment. Environment IDs exclude trial identity and policy sampling; run IDs include trial/config/policy metadata. Fixed explicit task_seed across base seeds intentionally repeats a task. Use a task-seed series for independent environments and multiple trial IDs within each. Do not treat repeated trials within an environment as independent environments in uncertainty estimates.

Every request records the prompt, action schema, observation, settings, run, environment and trial identities. Responses record parsed actions, raw provider response, request ID, status and usage when supplied by an `EvidenceResponse` transport. Mocks label usage as mock/unknown instead of inventing actual token consumption. Failures retain partial simulation events; refusals/incomplete responses produce failed runs and no substituted answer. No automatic retry or paid execution is built into this task.

`EvidenceReplayAgent` consumes saved audit records for a selected run and rejects changed context/observations. Its bind hook ties every action to run/environment/trial/actor/turn. This validates the saved trajectory, not deterministic behavior from new provider calls. Provider credentials must never be included in returned raw responses or settings.

Offline strategies are `retrieve`, `copy`, and `abstain`. Their outcomes test cost enforcement, natural-language message delivery, citation checks and controls, not LLM behavior. Next validation should pre-specify verification-cost treatments, evidence difficulty, held-out task seeds, repeated model samples and reporting of refusals/failures; compare factual accuracy, grounding, spending and completion before expanding scale.
