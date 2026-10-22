"""Decision table validation, evaluation, replay, comparison, and export."""

from __future__ import annotations

import html
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


class ModelError(ValueError):
    """An actionable model or case error."""


def need(ok: bool, message: str) -> None:
    if not ok:
        raise ModelError(message)


def string(value: Any, where: str) -> None:
    need(isinstance(value, str) and bool(value.strip()), f"{where} must be a non-empty string")


def validate_model(model: dict, require_confirmed: bool = False) -> None:
    need(isinstance(model, dict), "model must be an object")
    need(isinstance(model.get("schema_version"), int) and not isinstance(model.get("schema_version"), bool) and model["schema_version"] == 1, "schema_version must be integer 1")
    for key in ("id", "title", "revision"):
        string(model.get(key), key)
    inputs = model.get("inputs")
    outcomes = model.get("outcomes")
    rules = model.get("rules")
    need(isinstance(inputs, list), "inputs must be an array")
    need(isinstance(outcomes, list) and outcomes and all(isinstance(x, str) and x.strip() for x in outcomes), "outcomes must be a non-empty array of strings")
    need(len(set(outcomes)) == len(outcomes), "outcomes must be unique")
    need(isinstance(rules, list), "rules must be an array")
    specs: dict[str, dict] = {}
    for i, spec in enumerate(inputs):
        need(isinstance(spec, dict), f"inputs[{i}] must be an object")
        name = spec.get("name")
        string(name, f"inputs[{i}].name")
        need(name not in specs, f"duplicate input name: {name}")
        kind = spec.get("type")
        need(isinstance(kind, str) and kind in {"enum", "boolean", "integer"}, f"input {name} type must be enum, boolean, or integer")
        if kind == "enum":
            vals = spec.get("values")
            need(isinstance(vals, list) and bool(vals) and all(isinstance(x, str) and x.strip() for x in vals), f"input {name}.values must be non-empty strings")
            need(len(set(vals)) == len(vals), f"input {name}.values must be unique")
        if kind == "integer":
            for bound in ("minimum", "maximum"):
                if bound in spec:
                    need(isinstance(spec[bound], int) and not isinstance(spec[bound], bool), f"input {name}.{bound} must be an integer")
            if "minimum" in spec and "maximum" in spec:
                need(spec["minimum"] <= spec["maximum"], f"input {name} minimum exceeds maximum")
        specs[name] = spec
    rule_ids: set[str] = set()
    for i, rule in enumerate(rules):
        need(isinstance(rule, dict), f"rules[{i}] must be an object")
        rid = rule.get("id")
        string(rid, f"rules[{i}].id")
        need(rid not in rule_ids, f"duplicate rule id: {rid}")
        rule_ids.add(rid)
        need(isinstance(rule.get("outcome"), str) and rule.get("outcome") in outcomes, f"rule {rid} has unknown outcome")
        status = rule.get("review_status")
        need(isinstance(status, str) and status in {"confirmed", "draft"}, f"rule {rid}.review_status must be confirmed or draft")
        if require_confirmed:
            need(status == "confirmed", f"rule {rid} is draft; resolve its review_status before evaluation")
        when = rule.get("when")
        need(isinstance(when, dict), f"rule {rid}.when must be an object")
        for input_name, condition in when.items():
            need(input_name in specs, f"rule {rid} refers to unknown input {input_name}")
            validate_condition(condition, specs[input_name], f"rule {rid}.{input_name}")
        if "source_refs" in rule:
            need(isinstance(rule["source_refs"], list), f"rule {rid}.source_refs must be an array")
            for j, ref in enumerate(rule["source_refs"]):
                need(isinstance(ref, dict), f"rule {rid}.source_refs[{j}] must be an object")
                string(ref.get("path"), f"rule {rid} source path")
                portable_path = ref["path"].replace("\\", "/")
                windows_path = PureWindowsPath(ref["path"])
                need(not windows_path.drive and not windows_path.is_absolute() and not portable_path.startswith("/") and ".." not in PurePosixPath(portable_path).parts, f"rule {rid} source path must stay relative")
                for key in ("line_start", "line_end"):
                    need(isinstance(ref.get(key), int) and not isinstance(ref.get(key), bool) and ref[key] > 0, f"rule {rid} source {key} must be a positive integer")
                need(ref["line_end"] >= ref["line_start"], f"rule {rid} source range is reversed")


def validate_condition(condition: Any, spec: dict, where: str) -> None:
    need(isinstance(condition, dict) and len(condition) == 1, f"{where} must contain exactly one condition operator")
    op, value = next(iter(condition.items()))
    need(isinstance(op, str) and op in {"eq", "in", "gte", "lte"}, f"{where} uses unsupported operator {op}")
    kind = spec["type"]
    if op in {"gte", "lte"}:
        need(kind == "integer", f"{where} uses {op} on a non-integer input")
        need(isinstance(value, int) and not isinstance(value, bool), f"{where}.{op} must be an integer")
    elif op == "in":
        need(isinstance(value, list) and bool(value), f"{where}.in must be a non-empty array")
        for item in value:
            _validate_literal(item, spec, where)
        need(len(set(value)) == len(value), f"{where}.in values must be unique")
    else:
        _validate_literal(value, spec, where)


def _validate_literal(value: Any, spec: dict, where: str) -> None:
    kind = spec["type"]
    if kind == "enum":
        need(isinstance(value, str) and value in spec["values"], f"{where} has a value outside its enum domain")
    elif kind == "boolean":
        need(isinstance(value, bool), f"{where} requires a boolean value")
    else:
        need(isinstance(value, int) and not isinstance(value, bool), f"{where} requires an integer value")
        if "minimum" in spec:
            need(value >= spec["minimum"], f"{where} is below the input minimum")
        if "maximum" in spec:
            need(value <= spec["maximum"], f"{where} exceeds the input maximum")


def _validate_inputs(model: dict, values: dict) -> None:
    need(isinstance(values, dict), "inputs must be an object")
    specs = {x["name"]: x for x in model["inputs"]}
    unknown = sorted(set(values) - set(specs))
    need(not unknown, "unknown input key(s): " + ", ".join(unknown))
    for name, value in values.items():
        _validate_literal(value, specs[name], f"input {name}")


def evaluate(model: dict, inputs: dict) -> dict:
    validate_model(model, require_confirmed=True)
    _validate_inputs(model, inputs)
    results = []
    matched = []
    unknown_rules = []
    missing: set[str] = set()
    for rule in model["rules"]:
        conditions = []
        saw_unknown = False
        saw_false = False
        rule_missing: set[str] = set()
        for name, condition in rule["when"].items():
            if name not in inputs:
                state, detail = "unknown", f"{name} is missing"
                saw_unknown = True
                rule_missing.add(name)
            else:
                value = inputs[name]
                op, expected = next(iter(condition.items()))
                if op == "eq":
                    ok = value == expected
                    detail = f"{name} equals {json.dumps(expected)}" if ok else f"{name} is {json.dumps(value)}, expected {json.dumps(expected)}"
                elif op == "in":
                    ok = value in expected
                    detail = f"{name} is in the listed values" if ok else f"{name} is not in the listed values"
                elif op == "gte":
                    ok = value >= expected
                    detail = f"{name} is at least {expected}" if ok else f"{name} is below {expected}"
                else:
                    ok = value <= expected
                    detail = f"{name} is at most {expected}" if ok else f"{name} is above {expected}"
                state = "match" if ok else "no_match"
                saw_false |= not ok
            conditions.append({"input": name, "state": state, "detail": detail})
        state = "no_match" if saw_false else "unknown" if saw_unknown else "match"
        if state == "match":
            matched.append(rule)
        elif state == "unknown":
            unknown_rules.append(rule["id"])
            missing.update(rule_missing)
        results.append({"rule_id": rule["id"], "state": state, "outcome": rule["outcome"], "conditions": conditions})
    if unknown_rules:
        status, outcome = "missing", None
    else:
        outcomes = list(dict.fromkeys(rule["outcome"] for rule in matched))
        if not outcomes:
            status, outcome = "unresolved", None
        elif len(outcomes) > 1:
            status, outcome = "conflict", None
        else:
            status, outcome = "resolved", outcomes[0]
    return {"status": status, "outcome": outcome, "matched_rule_ids": [x["id"] for x in matched], "unknown_rule_ids": unknown_rules, "missing_inputs": sorted(missing), "rule_results": results, "prediction_label": "model prediction"}


def validate_cases(model: dict, cases: dict) -> None:
    need(isinstance(cases, dict) and isinstance(cases.get("schema_version"), int) and not isinstance(cases.get("schema_version"), bool) and cases["schema_version"] == 1, "cases schema_version must be integer 1")
    rows = cases.get("cases")
    need(isinstance(rows, list), "cases must be an array")
    ids: set[str] = set()
    for i, case in enumerate(rows):
        need(isinstance(case, dict), f"cases[{i}] must be an object")
        cid = case.get("id")
        string(cid, f"cases[{i}].id")
        need(cid not in ids, f"duplicate case id: {cid}")
        ids.add(cid)
        _validate_inputs(model, case.get("inputs"))
        expected = case.get("expected")
        need(expected is None or isinstance(expected, dict), f"case {cid}.expected must be an object or null")
        if expected is not None:
            need(isinstance(expected.get("review_status"), str) and expected.get("review_status") in {"proposed", "confirmed"}, f"case {cid}.expected.review_status must be proposed or confirmed")
            if expected["review_status"] == "confirmed":
                need(expected.get("outcome") in model["outcomes"], f"case {cid} confirmed expected outcome is unknown")
                string(expected.get("reviewer"), f"case {cid}.expected.reviewer")
            elif "outcome" in expected:
                need(expected["outcome"] in model["outcomes"], f"case {cid} proposed expected outcome is unknown")


def replay(model: dict, cases: dict) -> dict:
    validate_model(model, require_confirmed=True)
    validate_cases(model, cases)
    rows = []
    for case in cases["cases"]:
        prediction = evaluate(model, case["inputs"])
        exp = case.get("expected")
        expectation_status = "absent" if exp is None else ("confirmed" if exp["review_status"] == "confirmed" else "proposed")
        if expectation_status != "confirmed":
            comparison = "not_scored"
        elif prediction["status"] == "resolved" and prediction["outcome"] == exp["outcome"]:
            comparison = "match"
        else:
            comparison = "mismatch"
        rows.append({"id": case["id"], "inputs": case["inputs"], "expectation_status": expectation_status, "expected_outcome": exp.get("outcome") if exp else None, "reviewer": exp.get("reviewer") if exp else None, "comparison": comparison, "prediction": prediction})
    return {"schema_version": 1, "model_id": model["id"], "revision": model["revision"], "cases": rows}


def _input_signature(model: dict) -> list[tuple]:
    return [(x["name"], x["type"], tuple(x.get("values", [])), x.get("minimum"), x.get("maximum")) for x in model["inputs"]]


def compare_models(old: dict, new: dict, cases: dict) -> dict:
    validate_model(old, require_confirmed=True)
    validate_model(new, require_confirmed=True)
    need(_input_signature(old) == _input_signature(new), "cannot compare models with incompatible input schemas")
    need(old["outcomes"] == new["outcomes"], "cannot compare models with incompatible outcome vocabularies")
    validate_cases(old, cases)
    changes = []
    for case in cases["cases"]:
        before, after = evaluate(old, case["inputs"]), evaluate(new, case["inputs"])
        changed = (before["status"], before["outcome"]) != (after["status"], after["outcome"])
        explanation_changed = before["matched_rule_ids"] != after["matched_rule_ids"]
        changes.append({"id": case["id"], "inputs": case["inputs"], "before": {"status": before["status"], "outcome": before["outcome"], "matched_rule_ids": before["matched_rule_ids"]}, "after": {"status": after["status"], "outcome": after["outcome"], "matched_rule_ids": after["matched_rule_ids"]}, "prediction_changed": changed, "explanation_changed": explanation_changed})
    return {"schema_version": 1, "old_revision": old["revision"], "new_revision": new["revision"], "cases": changes}


def export_confirmed(model: dict, cases: dict) -> dict:
    result = replay(model, cases)
    confirmed = []
    for row in result["cases"]:
        if row["expectation_status"] != "confirmed":
            continue
        confirmed.append({"id": row["id"], "inputs": row["inputs"], "expected_outcome": row["expected_outcome"], "reviewer": row["reviewer"], "predicted_status": row["prediction"]["status"], "predicted_outcome": row["prediction"]["outcome"], "matched_rule_ids": row["prediction"]["matched_rule_ids"], "comparison": row["comparison"]})
    return {"schema_version": 1, "model_id": model["id"], "revision": model["revision"], "cases": confirmed, "predictions": [{"id": row["id"], "status": row["prediction"]["status"], "outcome": row["prediction"]["outcome"], "expectation_status": row["expectation_status"], "comparison": row["comparison"]} for row in result["cases"]]}


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def render_html(model: dict) -> str:
    validate_model(model, require_confirmed=True)
    def safe_integer_literals(value):
        if type(value) is int:
            need(abs(value) <= 9007199254740991, "HTML export requires integer literals within JavaScript safe integer range")
        elif isinstance(value, dict):
            for child in value.values(): safe_integer_literals(child)
        elif isinstance(value, list):
            for child in value: safe_integer_literals(child)
    safe_integer_literals(model)
    css = (Path(__file__).parent / "workbench.css").read_text(encoding="utf-8")
    js = (Path(__file__).parent / "workbench.js").read_text(encoding="utf-8")
    title = html.escape(model["title"])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · Intent Workbench</title><style>{css}</style></head>
<body><main class="app"><header class="topbar"><a class="brand" href="#top" aria-label="Intent Workbench home"><span class="brand-mark">IW</span><span>DECISION ROOM</span></a><p>Revision {html.escape(model['revision'])} <i aria-hidden="true"></i> Offline model snapshot</p></header>
<section class="hero" id="top"><div><p class="eyebrow">BEHAVIOR TABLE / {html.escape(model['id']).upper()}</p><h1>{title}</h1><p class="lede">Set only the facts you know. The table will show when rules agree, disagree, or still need a decision.</p></div><div class="status-key"><span><b class="dot resolved"></b>Resolved</span><span><b class="dot missing"></b>Missing</span><span><b class="dot conflict"></b>Conflict</span><span><b class="dot unresolved"></b>Unresolved</span></div></section>
<section class="form-panel"><div class="panel-head"><div><p class="eyebrow">TRY A CASE</p><h2>What is true?</h2></div><div class="actions"><button id="download" type="button" class="quiet">Download case JSON</button><button id="reset" type="button" class="quiet">Reset inputs</button></div></div><div id="fields" class="fields"></div></section>
<section class="result-grid"><article class="verdict" aria-live="polite" aria-atomic="true"><p class="eyebrow">MODEL PREDICTION</p><p id="verdict-status" class="verdict-status">Set inputs to evaluate</p><h2 id="verdict-outcome">—</h2><p id="missing"></p><p class="boundary">This result describes the reviewed table. It does not authorize or perform a real action.</p></article><article class="rule-panel"><div class="panel-head"><div><p class="eyebrow">WHY THIS RESULT</p><h2>Rule trace</h2></div><span id="rule-count"></span></div><div id="rules"></div></article></section>
<p class="footnote">Model {html.escape(model['id'])} · revision {html.escape(model['revision'])}. This page is a local snapshot. Downloaded inputs and predictions carry no reviewer confirmation.</p><noscript><p class="noscript">Enable JavaScript to evaluate this authored decision table. This page does not execute a production policy.</p></noscript></main>
<script type="application/json" id="model-data">{_safe_json(model)}</script><script>{js}</script></body></html>'''
