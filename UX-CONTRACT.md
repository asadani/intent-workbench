# Intent Workbench UI Contract

## Product context

- Audience: PMs and engineers clarifying a bounded behavior before implementation.
- Primary job: set known inputs, inspect model prediction and rule matches, and save an unconfirmed case.
- Market and locale: general technical audience; English copy with system font fallbacks.
- Runtime: single offline HTML snapshot of one confirmed model revision.
- Business authority: `docs/PLAN.md` and `PRODUCT.md`; sample sharing policies are synthetic and do not authorize real access.
- Visual tokens and rationale: [`DESIGN.md`](DESIGN.md).

## Canonical UI Map

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
| --- | --- | --- | --- | --- |
| Form | Native controls and collect() in workbench.js | PRODUCT.md, docs/PLAN.md, and DESIGN.md | Enum, boolean, integer, each with unset state | Python tests and JavaScript evaluator parity; browser coverage pending |
| Select/Listbox | Native select created by workbench.js | DESIGN.md | Enum and boolean selectors; OS-owned popup | Native markup review; browser coverage pending |
| Scrollbar | Global workbench.css baseline | DESIGN.md | Document scrolling with forced-colors fallback | Static audit and stylesheet review; browser coverage pending |

## Canonical controls and behavior

| Capability | Canonical owner | Behavior |
|---|---|---|
| Input fields | Native labeled `select` or `input[type=number]` | Empty means unset. No value is inferred. Numeric range errors stay on the field and prevent evaluation. |
| Reset | Native button | Clears all values, reevaluates the empty case, then focuses the first input. |
| Evaluate | Inline deterministic evaluator | Shows resolved, missing, conflict, or unresolved with matching and unknown rule details. No rule priority is applied. |
| Download case JSON | Native button and local Blob download | Includes model revision, inputs, prediction, no expected outcome, and unconfirmed status. It does not mint a reviewer decision. |
| Rule trace | Text-only list | Preserves model rule order and explains each condition state. No user text is inserted as HTML. |
| Scrollbar | Global generated stylesheet | Visible page scrollbar uses the CSS standard properties plus WebKit styling, with forced-colors reset. |

No service calls, alerts, prompts, background mutations, or persistence are used. Model drafts prevent building the interactive page.

## Verification

- Unit and CLI coverage: `python -m unittest discover -s tests -v`.
- Python evaluator and inline JavaScript evaluator are compared over every shipped case.
- `node --check intent_workbench/workbench.js` checks JavaScript syntax.
- Browser behavior is not verified in this environment; README records this limitation.
