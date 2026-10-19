# Experiment 3: can finite oversight amplify failures?

## Operational task and local rules

Each agent independently receives at most one task per tick with probability `arrival_probability`. A task is hard with probability `difficulty`. In this toy task model, an unreviewed hard answer is always unsafe; an easy answer is safe. The scripted policy immediately answers easy tasks and escalates hard tasks. Review is perfect. Waiting tasks can retry and, at a fixed deadline, answer unsafely with probability `impatience`, otherwise abstain. The global outcome is an unsafe answer count, not an external action.

Every original task is a distinct provenance root. Retry requests reference that root; review service references the exact queued request. Agents can have multiple outstanding tasks; no bounded private workload, token budget, arrival feedback or inter-agent communication is imposed.

## Update order

For ticks 0 through `ticks-1`:

1. Service eligible review requests in FIFO order, within capacity. A pending task becomes reviewed and safe. Stale requests still consume review capacity, explicitly modeling duplicate-processing waste.
2. For existing pending tasks, apply deadline choices first, then retries for nonexpired tasks at multiples of `retry_interval`.
3. Generate new tasks and apply arrival decisions; enqueue escalations.
4. Record queued requests, distinct pending tasks and cumulative unsafe answers.

Requests become eligible at enqueue tick + max(1, review_latency). Review occurs before deadline actions on the same tick. Arrivals continue at the final tick; there is no drain period. Consequently, even unlimited review can leave newly arrived tasks unresolved. Deadlines do not remove already queued requests. An unlimited queue budget still respects latency, so long latency can cause deadline failures even without capacity constraints.

## Treatments and controls

- `feedback`: waiting tasks add duplicate requests at each retry opportunity. Stale duplicates remain until serviced.
- `no_retries`: only the original request is enqueued.
- `deduplicated`: retry attempts are recorded but suppressed if that task already has a queued request.
- `unbounded`: process every eligible request each tick; retains the same latency and retry rule.
- `capacity_scaling=fixed`: total reviews per tick are `review_capacity`.
- `capacity_scaling=proportional`: capacity is ceil(review_capacity * n / reference_population). Rounding matters for small populations and is reported as effective capacity.

Arrival and difficulty draws are paired across arms using semantic random keys. The pilot varies arrival probability at fixed n=8, capacity=2 and 32 ticks, with twelve seeds: 192 runs. A separate unrun scaling config compares n=4/8/16 with fixed and proportional review budgets. The task-load increase with population is intentional in that scaling config; fixed-total-arrival designs would answer a different question.

## Measurements

Unsafe fraction uses all arrived tasks as denominator, including those pending at the horizon. We therefore also report raw counts and pending tasks; short horizons can suppress the observed fraction. `answered` includes unsafe answers, while `reviewed` denotes unique tasks resolved by review. Task conservation is arrivals = answered + reviewed + abstained + pending.

Backlog is queued requests, not distinct jobs. Metrics separately report retries, suppressed retries, stale/wasted reviews, serviced requests and unique pending tasks. Mean completed review delay includes only successfully reviewed tasks and excludes pending or deadline-resolved tasks; it must not be read as an unbiased overall waiting-time estimate. No recovery-time or queue-stationarity estimate is made.

The initial pilot reports means and run-level percentile bootstrap intervals. These are descriptive comparisons, not a criticality test or evidence of a phase transition. Growing backlog above service capacity is an ordinary queueing outcome; the causal question here is the additional effect of imposed retry feedback versus matched controls. Mechanisms such as longer delays leading to new failures that create new tasks are not implemented; only waiting-driven retry amplification is present.

## Later agent experiments

`ActionPolicy.choose` receives an arrival or deadline observation and returns a restricted action. Retries remain an environment rule in this baseline. Future work should allow agent-controlled retries, explicit utility/cost tradeoffs, imperfect reviewers and measured task difficulty. A real LLM's uncertainty signal must replace the oracle `requires_review` flag before interpreting behavior as realistic oversight dynamics.
