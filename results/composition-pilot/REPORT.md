# Composition scripted pilot

Completed 864 runs. No LLM or external tool calls.

These are finite synthetic experiments under explicit rules, not validated LLM behavior or evidence of phase transitions. Intervals use 1,000 run-level bootstrap resamples; repeated seeds are paired across treatments, not extra independent evidence.

| Control | Authorization | Relays | Retention | Disclosure mean | 95% interval |
|---|---|---:|---:|---:|---|
| intact | local | 0 | 0.0 | 1.000 | [1.000, 1.000] |
| intact | local | 2 | 0.0 | 1.000 | [1.000, 1.000] |
| intact | local | 0 | 0.5 | 1.000 | [1.000, 1.000] |
| intact | local | 2 | 0.5 | 1.000 | [1.000, 1.000] |
| intact | local | 0 | 1.0 | 1.000 | [1.000, 1.000] |
| intact | local | 2 | 1.0 | 1.000 | [1.000, 1.000] |
| remove_retriever | local | 0 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_retriever | local | 2 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_retriever | local | 0 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_retriever | local | 2 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_retriever | local | 0 | 1.0 | 0.000 | [0.000, 0.000] |
| remove_retriever | local | 2 | 1.0 | 0.000 | [0.000, 0.000] |
| remove_transform | local | 0 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_transform | local | 2 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_transform | local | 0 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_transform | local | 2 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_transform | local | 0 | 1.0 | 0.000 | [0.000, 0.000] |
| remove_transform | local | 2 | 1.0 | 0.000 | [0.000, 0.000] |
| remove_publisher | local | 0 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_publisher | local | 2 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_publisher | local | 0 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_publisher | local | 2 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_publisher | local | 0 | 1.0 | 0.000 | [0.000, 0.000] |
| remove_publisher | local | 2 | 1.0 | 0.000 | [0.000, 0.000] |
| cut_handoff | local | 0 | 0.0 | 0.000 | [0.000, 0.000] |
| cut_handoff | local | 2 | 0.0 | 0.000 | [0.000, 0.000] |
| cut_handoff | local | 0 | 0.5 | 0.000 | [0.000, 0.000] |
| cut_handoff | local | 2 | 0.5 | 0.000 | [0.000, 0.000] |
| cut_handoff | local | 0 | 1.0 | 0.000 | [0.000, 0.000] |
| cut_handoff | local | 2 | 1.0 | 0.000 | [0.000, 0.000] |
| sanitize | local | 0 | 0.0 | 0.000 | [0.000, 0.000] |
| sanitize | local | 2 | 0.0 | 0.000 | [0.000, 0.000] |
| sanitize | local | 0 | 0.5 | 0.000 | [0.000, 0.000] |
| sanitize | local | 2 | 0.5 | 0.000 | [0.000, 0.000] |
| sanitize | local | 0 | 1.0 | 0.000 | [0.000, 0.000] |
| sanitize | local | 2 | 1.0 | 0.000 | [0.000, 0.000] |
| intact | declared | 0 | 0.0 | 1.000 | [1.000, 1.000] |
| intact | declared | 2 | 0.0 | 1.000 | [1.000, 1.000] |
| intact | declared | 0 | 0.5 | 0.750 | [0.500, 1.000] |
| intact | declared | 2 | 0.5 | 0.875 | [0.625, 1.000] |
| intact | declared | 0 | 1.0 | 0.000 | [0.000, 0.000] |
| intact | declared | 2 | 1.0 | 0.000 | [0.000, 0.000] |
| remove_retriever | declared | 0 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_retriever | declared | 2 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_retriever | declared | 0 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_retriever | declared | 2 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_retriever | declared | 0 | 1.0 | 0.000 | [0.000, 0.000] |
| remove_retriever | declared | 2 | 1.0 | 0.000 | [0.000, 0.000] |
| remove_transform | declared | 0 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_transform | declared | 2 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_transform | declared | 0 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_transform | declared | 2 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_transform | declared | 0 | 1.0 | 0.000 | [0.000, 0.000] |
| remove_transform | declared | 2 | 1.0 | 0.000 | [0.000, 0.000] |
| remove_publisher | declared | 0 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_publisher | declared | 2 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_publisher | declared | 0 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_publisher | declared | 2 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_publisher | declared | 0 | 1.0 | 0.000 | [0.000, 0.000] |
| remove_publisher | declared | 2 | 1.0 | 0.000 | [0.000, 0.000] |
| cut_handoff | declared | 0 | 0.0 | 0.000 | [0.000, 0.000] |
| cut_handoff | declared | 2 | 0.0 | 0.000 | [0.000, 0.000] |
| cut_handoff | declared | 0 | 0.5 | 0.000 | [0.000, 0.000] |
| cut_handoff | declared | 2 | 0.5 | 0.000 | [0.000, 0.000] |
| cut_handoff | declared | 0 | 1.0 | 0.000 | [0.000, 0.000] |
| cut_handoff | declared | 2 | 1.0 | 0.000 | [0.000, 0.000] |
| sanitize | declared | 0 | 0.0 | 0.000 | [0.000, 0.000] |
| sanitize | declared | 2 | 0.0 | 0.000 | [0.000, 0.000] |
| sanitize | declared | 0 | 0.5 | 0.000 | [0.000, 0.000] |
| sanitize | declared | 2 | 0.5 | 0.000 | [0.000, 0.000] |
| sanitize | declared | 0 | 1.0 | 0.000 | [0.000, 0.000] |
| sanitize | declared | 2 | 1.0 | 0.000 | [0.000, 0.000] |
| intact | lineage | 0 | 0.0 | 0.000 | [0.000, 0.000] |
| intact | lineage | 2 | 0.0 | 0.000 | [0.000, 0.000] |
| intact | lineage | 0 | 0.5 | 0.000 | [0.000, 0.000] |
| intact | lineage | 2 | 0.5 | 0.000 | [0.000, 0.000] |
| intact | lineage | 0 | 1.0 | 0.000 | [0.000, 0.000] |
| intact | lineage | 2 | 1.0 | 0.000 | [0.000, 0.000] |
| remove_retriever | lineage | 0 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_retriever | lineage | 2 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_retriever | lineage | 0 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_retriever | lineage | 2 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_retriever | lineage | 0 | 1.0 | 0.000 | [0.000, 0.000] |
| remove_retriever | lineage | 2 | 1.0 | 0.000 | [0.000, 0.000] |
| remove_transform | lineage | 0 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_transform | lineage | 2 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_transform | lineage | 0 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_transform | lineage | 2 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_transform | lineage | 0 | 1.0 | 0.000 | [0.000, 0.000] |
| remove_transform | lineage | 2 | 1.0 | 0.000 | [0.000, 0.000] |
| remove_publisher | lineage | 0 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_publisher | lineage | 2 | 0.0 | 0.000 | [0.000, 0.000] |
| remove_publisher | lineage | 0 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_publisher | lineage | 2 | 0.5 | 0.000 | [0.000, 0.000] |
| remove_publisher | lineage | 0 | 1.0 | 0.000 | [0.000, 0.000] |
| remove_publisher | lineage | 2 | 1.0 | 0.000 | [0.000, 0.000] |
| cut_handoff | lineage | 0 | 0.0 | 0.000 | [0.000, 0.000] |
| cut_handoff | lineage | 2 | 0.0 | 0.000 | [0.000, 0.000] |
| cut_handoff | lineage | 0 | 0.5 | 0.000 | [0.000, 0.000] |
| cut_handoff | lineage | 2 | 0.5 | 0.000 | [0.000, 0.000] |
| cut_handoff | lineage | 0 | 1.0 | 0.000 | [0.000, 0.000] |
| cut_handoff | lineage | 2 | 1.0 | 0.000 | [0.000, 0.000] |
| sanitize | lineage | 0 | 0.0 | 0.000 | [0.000, 0.000] |
| sanitize | lineage | 2 | 0.0 | 0.000 | [0.000, 0.000] |
| sanitize | lineage | 0 | 0.5 | 0.000 | [0.000, 0.000] |
| sanitize | lineage | 2 | 0.5 | 0.000 | [0.000, 0.000] |
| sanitize | lineage | 0 | 1.0 | 0.000 | [0.000, 0.000] |
| sanitize | lineage | 2 | 1.0 | 0.000 | [0.000, 0.000] |

Minimum violating coalitions and leave-one-out controls are evaluated exactly for this fixed scripted workflow, not for arbitrary agent organizations. Visible labels can be dropped while the environment retains true ancestry. The lineage gate conservatively blocks restricted descendants, including sanitized descendants; redaction is not implicit declassification.

Full configurations and bootstrap intervals: summary.csv. Seed-level outcomes: runs.csv. Parent-linked traces: runs/*.events.jsonl.gz. See the experiment protocol under docs/ for update order, denominators and limitations.
