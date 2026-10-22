# Intent Workbench v0.1 implementation plan

## User job

Evaluate a bounded, confirmed decision table against concrete inputs; show missing information and conflicting outcomes; compare two revisions; export confirmed expectations. Generate an offline HTML case editor from the same model.

## CLI

```sh
python -m intent_workbench validate fixtures/sharing-v1.json
python -m intent_workbench evaluate fixtures/sharing-v1.json --input fixtures/input.json --out evaluation.json
python -m intent_workbench replay fixtures/sharing-v1.json fixtures/cases.json --out replay.json
python -m intent_workbench compare fixtures/sharing-v1.json fixtures/sharing-v2.json fixtures/cases.json --out comparison.json
python -m intent_workbench export fixtures/sharing-v2.json fixtures/cases.json --out confirmed-fixtures.json
python -m intent_workbench build fixtures/sharing-v2.json --out workbench.html
```

`evaluate` returns 1 for missing/conflict/unresolved; `replay` returns 1 for any unresolved model case or mismatch against a confirmed expectation. `compare` always returns 0 for a successfully produced comparison; changed predictions are its output, not an execution error. `export` includes only cases with confirmed expectations, plus predictions kept separately. Draft/unconfirmed rules are never executed as accepted rules: reject models containing them with an actionable instruction to resolve their status before evaluation/build. Validation may accept drafts to support authoring, but reports their presence.

## Formats and semantics

Model: `{schema_version:1,id,title,revision,inputs:[{name,type,values?}],outcomes:[string],rules:[{id,when:{input_name:condition},outcome,review_status,source_refs?:[{path,line_start,line_end}],rationale?}]}`. Input types are `enum` (nonempty unique string values), `boolean`, or `integer`. A condition is exactly `{eq:value}`, `{in:[value,...]}`, `{gte:integer}`, or `{lte:integer}`. Numeric operators only apply to integer inputs. No expressions, nested boolean grammar, coercion, or rule priority. `when:{}` is an explicit always-match rule. All rule conditions combine with AND. Omitted fields in a rule are wildcards. Validate condition values against input types/domains. Input names, rule IDs, and outcome strings are unique; rules refer only to known inputs/outcomes. Unknown input keys and out-of-domain values are errors; absent defined inputs are allowed so missing information can be diagnosed.

Evaluation computes each rule as `match`, `no_match`, or `unknown`, with condition-level explanation. A false condition makes the rule no_match even if another condition is unknown. Otherwise any missing required condition input makes the rule unknown. If any unknown rules remain, overall status is `missing`, outcome null, and missing input names are listed; show known matching rules as context. With no unknowns, no matches gives `unresolved`; matches with one distinct outcome give `resolved`; matches with multiple distinct outcomes give `conflict`. Multiple rules agreeing on one outcome are allowed. Never apply first-match-wins or an implicit deny/allow default.

An evaluation is `{status,outcome,matched_rule_ids,unknown_rule_ids,missing_inputs,rule_results}` in model order. It explicitly labels outcome as a model prediction. Changing unused input values need not change predictions.

Cases: `{schema_version:1,cases:[{id,inputs,expected:{outcome,review_status:"proposed"|"confirmed",reviewer?:string,note?:string}}]}`. `expected` may be null; a confirmed expectation requires nonempty reviewer and a valid outcome. Case IDs unique. Replay preserves every case and reports `expectation_status: confirmed|proposed|absent` plus `comparison: match|mismatch|not_scored`; only confirmed expectations are scored, and unresolved/conflicting predictions cannot match a confirmed outcome. Comparison evaluates both models independently and marks prediction changes using `(status,outcome)`; include changed matching-rule IDs separately as explanation changes. Reject incompatible input schemas or outcome vocabularies between versions with a clear error rather than silently recoding cases.

## Core API

- `validate_model(model: dict, require_confirmed: bool = False) -> None`
- `evaluate(model: dict, inputs: dict) -> dict`
- `replay(model: dict, cases: dict) -> dict`
- `compare_models(old: dict, new: dict, cases: dict) -> dict`
- `export_confirmed(model: dict, cases: dict) -> dict`
- `render_html(model: dict) -> str`

The exported fixture has `schema_version`, model ID/revision, and cases containing inputs, `expected_outcome`, reviewer, `predicted_status`, `predicted_outcome`, and `matched_rule_ids`. A mismatch remains visible; export never edits a confirmed expectation to match a model.

## Offline interaction

Generate a single HTML file with labeled enum/boolean/integer controls and an explicit “unset” state. Evaluating shows outcome/status, matching rules, missing inputs, and condition explanations. A reset button clears inputs. Include a JSON download of the current inputs and model prediction, with expectation absent; UI interaction must not manufacture reviewer confirmation. Implement the same bounded evaluator in small inline JS with an explicit truth table matching Python; never eval user expressions. Embed all model content safely and display it through textContent. Document that the HTML is a snapshot of one model revision.

## Fixtures and acceptance tests

1. Sharing fixture has member/guest/editor roles, active_membership boolean, visibility enum, confirmed allow/deny rules, source rationale, and at least six cases. Include multiple matching rules that agree, a rule conflict, and a fully specified uncovered case.
2. Unknown input used by a possible rule gives missing. A known false condition plus a missing condition yields no_match for that rule. All cases assert exact status, outcome, matching/unknown rules, and missing field names.
3. Conflicting matches never select a default. Reordering rules does not change status/outcome, though explanation order follows the table.
4. Replay does not score proposed or absent expectations; a confirmed expected allow against unresolved or deny is a mismatch. Export retains that mismatch and excludes unconfirmed expectations.
5. v2 changes a rule; comparison identifies precisely the changed outcomes and distinguishes explanation-only changes. Incompatible schemas fail.
6. Reject duplicate IDs, unknown fields/operators, bool used as integer, out-of-domain literals, malformed conditions, and execution of draft rules. Preserve missing-input diagnosis as valid evaluation rather than malformed input.
7. CLI end-to-end smoke tests and escaping tests; manually exercise HTML unset inputs, resolved case, conflict, reset, and JSON download when a browser is available. Provide the same fixture truth-table cases for checking JS parity, and disclose any unverified browser behavior.

## Non-goals and milestone

No natural-language rule extraction, production authorization engine, group graph/inheritance resolution, stateful simulation, temporal policies, custom expressions, hosted app, or automatic approval. Define such derived facts as input fields only when a human has decided their meaning.

Build validated models plus pure evaluator first, then replay/compare/export, then the small offline editor. Done means the sharing demo exposes at least one conflict, one missing decision, and one intentional revision change while preserving reviewer expectations.
