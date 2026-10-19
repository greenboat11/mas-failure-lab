# Step 2: restricted-choice LLM pilot

The OpenAI Responses connection is implemented using the [official Structured Outputs format](https://developers.openai.com/api/docs/guides/structured-outputs). A real model, key and spending decision are still needed for live experiments. No provider is called by the default command:

```powershell
python -m mas_failure_lab.llm_pilot
```

The smoke configuration schedules eight runs and 128 requests: four agents, four ticks, four arms, two seeds. Each response is capped at 256 output tokens (32,768 total maximum output tokens). Input tokens also incur charges; no dollar estimate is asserted before choosing model/pricing. Call and output limits are **not a guaranteed dollar spending cap**. Reasoning models may require a larger output allowance; incomplete responses stop the experiment instead of retrying.

## Live execution, when a model and budget have been chosen

Configure `OPENAI_API_KEY` in the local environment using your normal secret-management method. Do not save it to this repository or paste it into the conversation. The command below is a template, not a live model recommendation:

```powershell
python -m mas_failure_lab.llm_pilot --execute --model YOUR_MODEL_ID --max-calls 128 --output results/local-llm
```

There is no automatic model selection, fallback, retry or resume. A missing key or insufficient call limit fails before requests. A transport error, refusal, incomplete response, invalid JSON or inaccessible provenance aborts the experiment. Re-running requires a fresh output directory and may incur costs again. No API key is logged.

## Audit and replay

`provider.jsonl` records each request before transmission and then its response or transport error. Requests contain full instructions, strict schema, model, observation, configuration and seed; responses contain the raw JSON, request ID, timing and reported token usage. Match `(config, seed, observation.tick, observation.agent)` to simulation decisions. Authorization headers and exception strings are excluded. Successful runs also retain compressed simulation event logs, outcomes and per-run decision counts. The manifest records attempted calls, completed runs, usage, source fingerprints and output checksums. Failed runs retain provider traces and previously completed runs; partial simulation event logs for the interrupted run are not yet saved.

`ReplayTransport(path)` replays successful audited responses offline, requiring identical observations and run context. Use the original model and agent settings from the manifest and set `replay.context` to `{"config": asdict(config), "seed": seed}` before each simulation. Call `assert_consumed()` after the full sweep. Replay validates the saved trajectory, not provider reproducibility. A new live run can produce different decisions even at identical settings.

`results/llm-mock/` contains a local integration exercise with a fake provider, explicitly labeled `source=mock`. Its synthetic token counts are test fixtures, not actual usage, and its outcomes are not LLM evidence.

Reproduce the local integration exercise with `python -m mas_failure_lab.llm_pilot --mock --output results/local-llm-mock`. This mode never sends a network request and requires no credentials.

## Scientific limits and next experimental decisions

This is a plumbing and action-choice pilot. It has stateless requests; agent memory is only the environment's current claim and supplied exposures. The correct document is visible on every request, verification is perfect and has no explicit penalty, and agents can only verify, retain or select an exposure. A model that always verifies is a valid outcome, not a reason to alter prompts until it fails. Scheduled recovery and monitor corrections remain imposed environment rules and must not be attributed to learned LLM recovery behavior.

The original scripted baseline's probability of verification/adoption does not constrain the LLM. The shared action schema and environment make choices comparable, but these decisions alone do not validate language-level propagation or actual collaboration. The smoke seeds include a shared-shock case to exercise integration; this two-seed selection is not suitable for estimating common-cause risk. No significance or phase-transition claims should be made from the smoke pilot.

After checking the connection, specify a larger held-out seed set, models/settings, repeated provider trials, budgets and 4/8/16-agent treatments. Separately design an evidence-retrieval treatment with explicit verification costs and natural-language messages. Preserve the original task as a control and report any prompt changes as new treatments. These extensions are not silently folded into this first pilot.
