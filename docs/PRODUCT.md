# Intent Workbench

Intent Workbench helps a PM and engineer make a proposed behavior concrete before implementation. They supply a small decision table, run cases, inspect which rules match, and retain explicitly confirmed expectations.

The first example concerns document sharing. Inputs describe the user's role, document visibility, and whether membership is active. One table intentionally omits a case; another contains conflicting rules. The evaluator returns “missing” or “conflict” with the relevant rule IDs instead of silently choosing a default. A revised table can be replayed against saved cases to show changes the team should discuss.

The durable output is a bounded rule model and a set of reviewed cases. An offline HTML workbench lets users edit input values and inspect outcomes without a server. Exported case fixtures distinguish actual model predictions from human-confirmed expectations.

The first release executes explicit rules; it does not translate prose into rules, model arbitrary access control, or prove that production software implements the intended policy. Terms such as group inheritance can be represented as already-established input facts, but their underlying semantics are outside this evaluator.

Validate it in real feature discussions by tracking unresolved decisions surfaced, preparation/correction effort, and cases reused during implementation. A deterministic answer is useful only when the team has inspected and accepted the rules that produced it.
