# Contributing

Run `python -m unittest discover -s tests -v` before submitting a change. Tests and default commands must remain local and credential-free. Add meaningful invariant, boundary or matched-control tests for changed mechanisms; avoid tests that only restate the implementation.

Document new transition rules, denominators, update order, randomness and censoring in the relevant protocol. Preserve prior pilot outputs; regenerate changed experiments into a new output folder and record provenance. Treat artifact checksums as evidence of the recorded run, not proof of a scientific conclusion.

Do not commit credentials, real restricted records, provider tokens or private conversations. Use synthetic fixtures. Real-provider experiments require explicit model/settings, usage logs and a separate budget decision. Keep observed behavior separate from environment-imposed transitions and label all mock outputs.

For a proposed phase-transition or criticality claim, first specify the size/horizon study, relevant nulls and theoretical assumptions. A steep curve or queue growing beyond capacity is insufficient by itself.
