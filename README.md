<p align="center">
  <img src="assets/logo.svg" alt="Intent Workbench — Make behavior explicit" width="400" height="160">
</p>

Intent Workbench evaluates a small confirmed decision table against explicit inputs. It shows when rules resolve, need missing facts, conflict, or leave a case uncovered. The document-sharing fixture includes a deliberate v1 conflict and a v2 revision that resolves it.

## Requirements

Python 3.11 or newer runs the CLI without third-party Python dependencies. JavaScript checks in the development test suite also require Node.js; local verification used Node.js 26.12.0. Opening the generated HTML needs a JavaScript-capable browser.

## Quickstart

Run from this repository directory with Python 3.11 or newer:

```sh
python -m intent_workbench --help
python -m intent_workbench validate fixtures/sharing-v1.json
```

Expected result: help exits `0`; validation prints `Valid model: document-sharing revision v1 (6 rules, 0 draft)` and exits `0`.

Evaluate the editor/inactive-member case. It intentionally matches allow and deny rules, so the completed check exits `1`:

```sh
python -m intent_workbench evaluate fixtures/sharing-v1.json --input fixtures/input.json --out /tmp/sharing-evaluation.json
```

The JSON reports `status: conflict`, a null outcome, and both matching rule IDs. It never picks the first rule. Replay the saved cases, compare revisions, and export confirmed expectations:

```sh
python -m intent_workbench replay fixtures/sharing-v1.json fixtures/cases.json --out /tmp/sharing-replay.json
python -m intent_workbench compare fixtures/sharing-v1.json fixtures/sharing-v2.json fixtures/cases.json --out /tmp/sharing-comparison.json
python -m intent_workbench export fixtures/sharing-v2.json fixtures/cases.json --out /tmp/confirmed-cases.json
python -m intent_workbench build fixtures/sharing-v2.json --out /tmp/intent-workbench.html
```

Expected results: replay exits `1` because the v1 conflict/mismatch remains visible; compare exits `0` and identifies the editor-inactive prediction change; export exits `0`, retaining confirmed expectations separately from predictions; build exits `0` and writes an offline HTML editor. The page has labeled unset inputs, a reset action, a rule trace, and a local JSON download with no expected outcome or reviewer confirmation.

Run the tests:

```sh
python -m unittest discover -s tests -v
```

Expected result: all tests pass with exit `0`. Coverage includes missing versus no-match conditions, conflict/order independence, expectations and export, revision comparison, invalid domains/operators, draft rejection, CLI exits, HTML escaping, JavaScript syntax, and Python/JavaScript evaluator parity over the shipped cases.

## Limits

Rules use only equality, membership, integer lower/upper bounds, and AND across one rule's listed conditions. There are no expressions, rule priorities, implicit allow/deny defaults, prose extraction, production enforcement, or group inheritance. Inputs are facts already supplied by a human; this tool does not establish their meaning. A prediction is not a production authorization decision. HTML is a local snapshot of one model revision. Browser interaction was not verified in this environment.

## Data integrity

HTML exports require numeric literals within JavaScript’s safe integer range, and interactive numeric inputs use the same range. The Python evaluator retains exact integer arithmetic. Output reports cannot overwrite their model or cases inputs.

See [verification coverage](docs/VERIFICATION.md) and [the design plan](docs/PLAN.md) for tested behavior and remaining limits.
