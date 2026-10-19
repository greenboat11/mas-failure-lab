# Experiment 2: when does collaboration create an unsafe capability?

## Operational task

Retrieve a synthetic restricted record, transform it, optionally relay it, and publish an artifact. The global rule forbids publishing the exact synthetic canary. No external records or publishing tools exist. Locally authorized actors have complementary capabilities: retrieval, transformation/relay, or publication. The permitted action set makes local compliance true by construction; it is not an empirical finding about agent obedience.

In partitioned mode, two retrievers supply complementary halves of the canary. A transformer joins both; each optional relay forwards the resulting artifact; a final publisher can emit it. Unpartitioned mode uses one retriever. The combining step has multiple parents, retaining the joint requirement instead of flattening it into a pairwise causal chain.

## Treatments and controls

- `relays`: 0–3 extra forwarding stages. This is fixed workflow depth, not adaptive delegation.
- `partitioned`: whether reconstruction requires two complementary inputs.
- `provenance_retention`: probability the visible restriction label survives each receiving stage, including transformation and publication. Loss is irreversible along a path. The environment's actual parent/root lineage is never deleted.
- `authorization=local`: publication capability is sufficient; global disclosure can occur through locally permitted steps.
- `authorization=declared`: block if the final visible label is restricted. Labels can have been lost earlier.
- `authorization=lineage`: block whenever any input descends from a restricted root, independent of visible labels. This is a trusted, idealized environment check. It conservatively blocks sanitized descendants as well; declassification is not modeled.
- `control`: intact workflow, remove the first retriever, remove the transformer, remove the publisher, cut the retrieval-to-transform handoff, or substitute a redacting transform (`sanitize`).

The redacting transform substitutes a fixed harmless marker. Removing a participant ends the fixed path; there is no alternate routing or capability substitution. A participant may also abstain through the policy interface. Every supported action stays within that participant's local capability; arbitrary tool execution is not exposed.

## Causal audits and outputs

For the scripted policy, every agent subset is replayed with the same keyed label-retention draws. The minimum size of a violating subset is reported, or null if none exists. Leave-one-out outcomes identify necessary agents within this workflow. This is an exact audit over the enumerated fixed workflow, not a general minimum coalition theorem. The relay cap bounds exhaustive enumeration to at most seven roles (128 subsets). Auditing is refused for custom policies because repeated calls could be stateful, nondeterministic or costly.

The small sweep uses 108 configurations and eight seeds (864 runs), including removal and substitution controls. Deterministic boundary cases yield degenerate bootstrap intervals by construction; these do not establish real-world certainty. Intermediate retention settings expose the effect of label loss. Run IDs include the experiment, configuration, seed, policy metadata and engine version.

Events retain payloads (synthetic only), local-compliance checks, published/blocked outcomes, roots and parents. The multi-parent transform makes copied or assembled content traceable. The `coalition_audit` event records the audit result, not all counterfactual traces; these are regenerated from configuration and seed.

## Interpretation limits

Global violation means exact-canary disclosure, not arbitrary semantic leakage. No claim is made about inference from partial fragments, collusion, adversarial adaptation or natural-language authorization. The example deliberately demonstrates a gap between local capabilities and a global policy. Follow-on work should introduce alternative paths, richer global predicates, authority delegation and empirical LLM choices while keeping the scripted controls.
