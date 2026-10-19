# Interchangeable agent interface

`simulate(config, seed, agent=...)` accepts any `Agent` with `metadata()` and `decide(observation, draws)`. The default is `ScriptedAgent(config.verification, config.adoption)`. An observation includes the synthetic task, evidence document, current integer claim and eligible exposure IDs. The environment owns graph access, scheduling, transitions, provenance and answer checking.

`Decision(verify=True)` rechecks D0 and corrects the claim. `Decision(adopt_event=id)` selects an available false exposure. `Decision()` retains the current claim. Verify and adopt are mutually exclusive. Fabricated or inaccessible provenance is rejected. This restricted action space enables a first controlled comparison, but is not a general language-synthesis environment.

```python
from mas_failure_lab.agents import LLMAgent
from mas_failure_lab.model import Config, simulate

def transport(observation):
    # Replace with a provider request and strict structured-response parsing.
    # This local fake makes no network calls.
    return {"verify": True, "adopt_event": None}

agent = LLMAgent(transport, model="local-fake", settings={"temperature": 0})
result = simulate(Config(n=4), seed=7, agent=agent)
```

Transport errors fail the run; there is no silent fallback or retry. The concrete `ResponsesTransport` now records prompts, schema, raw responses, request IDs, usage and timing; see [the LLM pilot](LLM_PILOT.md). The base `LLMAgent` remains provider-neutral and records normalized decisions. `ReplayTransport` supports exact offline replay of saved responses, not deterministic new provider calls. Scripted random draws are passed through the common interface but ignored by the LLM adapter. Compare verification/adoption behavior and costs empirically before parameterizing the simulator from LLM runs.
