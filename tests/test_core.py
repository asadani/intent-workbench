import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from intent_workbench.core import ModelError, compare_models, evaluate, export_confirmed, render_html, replay, validate_model


class Structure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.ids.update(value for name, value in attrs if name == "id")


def fixture(name):
    return json.loads((ROOT / "fixtures" / name).read_text())


class IntentCoreTests(unittest.TestCase):
    def setUp(self):
        self.v1 = fixture("sharing-v1.json")
        self.v2 = fixture("sharing-v2.json")
        self.cases = fixture("cases.json")

    def test_exact_evaluation_states_and_false_beats_unknown(self):
        resolved = evaluate(self.v2, {"role": "member", "active_membership": True, "visibility": "private"})
        self.assertEqual((resolved["status"], resolved["outcome"]), ("resolved", "allow"))
        self.assertEqual(resolved["matched_rule_ids"], ["member-active-private"])
        agreeing = evaluate(self.v2, {"role": "guest", "active_membership": True, "visibility": "link"})
        self.assertEqual(agreeing["status"], "resolved")
        self.assertEqual(agreeing["matched_rule_ids"], ["guest-link", "active-link-share"])
        missing = evaluate(self.v2, {"role": "member", "visibility": "private"})
        self.assertEqual(missing["status"], "missing")
        self.assertEqual(missing["missing_inputs"], ["active_membership"])
        self.assertEqual(missing["rule_results"][0]["state"], "unknown")
        self.assertEqual(missing["rule_results"][1]["state"], "no_match")
        partial = copy.deepcopy(self.v2)
        partial["rules"] = [{"id": "compound", "when": {"role": {"eq": "editor"}, "active_membership": {"eq": True}}, "outcome": "allow", "review_status": "confirmed"}]
        false_and_unknown = evaluate(partial, {"role": "guest"})
        self.assertEqual((false_and_unknown["status"], false_and_unknown["missing_inputs"]), ("unresolved", []))
        unresolved = evaluate(self.v2, {"role": "guest", "active_membership": True, "visibility": "private"})
        self.assertEqual((unresolved["status"], unresolved["outcome"]), ("unresolved", None))

    def test_conflicts_and_order_independence(self):
        inputs = {"role": "editor", "active_membership": False, "visibility": "private"}
        first = evaluate(self.v1, inputs)
        self.assertEqual((first["status"], first["outcome"]), ("conflict", None))
        self.assertEqual(first["matched_rule_ids"], ["editor-view", "inactive-member-deny"])
        reordered = copy.deepcopy(self.v1)
        reordered["rules"].reverse()
        second = evaluate(reordered, inputs)
        self.assertEqual((second["status"], second["outcome"]), ("conflict", None))
        self.assertEqual(second["matched_rule_ids"], list(reversed(first["matched_rule_ids"])))

    def test_replay_preserves_expectation_state_and_export_only_confirmed(self):
        replayed = replay(self.v1, self.cases)
        self.assertEqual([x["expectation_status"] for x in replayed["cases"]], ["confirmed", "confirmed", "confirmed", "confirmed", "absent", "proposed", "confirmed"])
        self.assertEqual(replayed["cases"][2]["comparison"], "mismatch")
        self.assertEqual(replayed["cases"][4]["comparison"], "not_scored")
        self.assertEqual(replayed["cases"][5]["comparison"], "not_scored")
        exported = export_confirmed(self.v2, self.cases)
        self.assertEqual(len(exported["cases"]), 5)
        self.assertEqual(next(x for x in exported["cases"] if x["id"] == "editor-inactive-conflict")["comparison"], "match")
        self.assertEqual(len(exported["predictions"]), len(self.cases["cases"]))

    def test_compare_reports_prediction_and_explanation_changes(self):
        result = compare_models(self.v1, self.v2, self.cases)
        changed = {row["id"]: row for row in result["cases"] if row["prediction_changed"]}
        self.assertEqual(set(changed), {"editor-inactive-conflict"})
        self.assertTrue(changed["editor-inactive-conflict"]["explanation_changed"])
        explanation_only = copy.deepcopy(self.v2)
        explanation_only["rules"][0]["id"] = "member-private-reviewed"
        result = compare_models(self.v2, explanation_only, self.cases)
        row = next(x for x in result["cases"] if x["id"] == "active-member-private")
        self.assertFalse(row["prediction_changed"])
        self.assertTrue(row["explanation_changed"])

    def test_validation_rejects_shapes_domains_and_drafts(self):
        bads = []
        m = copy.deepcopy(self.v1); m["schema_version"] = 1.0; bads.append((m, "integer 1"))
        m = copy.deepcopy(self.v1); m["rules"][0]["when"]["role"] = {"regex": "member"}; bads.append((m, "unsupported operator"))
        m = copy.deepcopy(self.v1); m["inputs"][0]["values"] = ["member", "member"]; bads.append((m, "unique"))
        m = copy.deepcopy(self.v1); m["rules"][0]["when"]["role"] = {"eq": "owner"}; bads.append((m, "outside its enum"))
        m = copy.deepcopy(self.v1); m["rules"][0]["when"]["unknown"] = {"eq": "x"}; bads.append((m, "unknown input"))
        m = copy.deepcopy(self.v1); m["rules"][0]["outcome"] = ["allow"]; bads.append((m, "unknown outcome"))
        for model, message in bads:
            with self.subTest(message=message), self.assertRaisesRegex(ModelError, message):
                validate_model(model)
        with self.assertRaisesRegex(ModelError, "unknown input key"):
            evaluate(self.v2, {"role": "member", "active_membership": True, "visibility": "private", "extra": True})

    def test_integer_validation_rejects_boolean_and_bounds(self):
        model = {"schema_version": 1, "id": "numeric", "title": "Numeric", "revision": "1", "inputs": [{"name": "attempts", "type": "integer", "minimum": 0, "maximum": 4}], "outcomes": ["retry"], "rules": [{"id": "retry-small", "when": {"attempts": {"lte": 2}}, "outcome": "retry", "review_status": "confirmed"}]}
        with self.assertRaisesRegex(ModelError, "requires an integer"):
            evaluate(model, {"attempts": True})
        with self.assertRaisesRegex(ModelError, "exceeds"):
            evaluate(model, {"attempts": 5})
        with self.assertRaisesRegex(ModelError, "must be an integer"):
            bad = copy.deepcopy(model); bad["rules"][0]["when"]["attempts"] = {"gte": True}; validate_model(bad)

    def test_draft_execution_and_incompatible_schema_fail(self):
        draft = copy.deepcopy(self.v2); draft["rules"][0]["review_status"] = "draft"
        with self.assertRaisesRegex(ModelError, "is draft"):
            evaluate(draft, {"role": "member"})
        incompatible = copy.deepcopy(self.v2); incompatible["inputs"][0]["values"].append("owner")
        with self.assertRaisesRegex(ModelError, "incompatible input schemas"):
            compare_models(self.v1, incompatible, self.cases)

    def test_html_is_offline_safe_and_has_native_controls(self):
        model = copy.deepcopy(self.v2); model["title"] = "Policy </script><script>attack()</script>"
        output = render_html(model)
        structure = Structure()
        structure.feed(output)
        self.assertTrue({"main", "button", "noscript"}.issubset(structure.tags))
        self.assertTrue({"fields", "verdict-status", "rules", "reset", "download"}.issubset(structure.ids))
        self.assertNotIn("</script><script>attack()", output)
        self.assertIn("\\u003c/script\\u003e", output)
        self.assertIn("aria-describedby", output)
        self.assertIn("textContent", output)
        self.assertNotIn("innerHTML", output)
        self.assertNotIn("fetch(", output)
        self.assertNotIn("alert(", output)
        self.assertIn('id="download"', output)

    def test_python_and_javascript_evaluators_match_fixture_truth_table(self):
        if not shutil.which("node"):
            self.skipTest("node is unavailable")
        script = ROOT / "intent_workbench/workbench.js"
        payload = json.dumps({"model": self.v2, "cases": [c["inputs"] for c in self.cases["cases"]]}, ensure_ascii=False)
        node_script = f"const {{evaluateModel}}=require({json.dumps(str(script))});const d={payload};process.stdout.write(JSON.stringify(d.cases.map(x=>evaluateModel(d.model,x))));"
        got = json.loads(subprocess.check_output(["node", "-e", node_script], text=True))
        expected = [evaluate(self.v2, c["inputs"]) for c in self.cases["cases"]]
        self.assertEqual(got, expected)
        subprocess.run(["node", "--check", str(script)], check=True, capture_output=True, text=True)

    def test_all_cli_commands_and_exit_contract(self):
        def run(*args):
            return subprocess.run([sys.executable, "-m", "intent_workbench", *args], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(run("--help").returncode, 0)
        self.assertEqual(run("--version").stdout.strip(), "0.1.0")
        self.assertEqual(run("validate", "fixtures/sharing-v1.json").returncode, 0)
        with tempfile.TemporaryDirectory() as temp:
            evaluation = run("evaluate", "fixtures/sharing-v1.json", "--input", "fixtures/input.json", "--out", f"{temp}/evaluation.json")
            self.assertEqual(evaluation.returncode, 1, evaluation.stderr)
            replayed = run("replay", "fixtures/sharing-v1.json", "fixtures/cases.json", "--out", f"{temp}/replay.json")
            self.assertEqual(replayed.returncode, 1, replayed.stderr)
            self.assertEqual(run("compare", "fixtures/sharing-v1.json", "fixtures/sharing-v2.json", "fixtures/cases.json", "--out", f"{temp}/comparison.json").returncode, 0)
            self.assertEqual(run("export", "fixtures/sharing-v2.json", "fixtures/cases.json", "--out", f"{temp}/export.json").returncode, 0)
            self.assertEqual(run("build", "fixtures/sharing-v2.json", "--out", f"{temp}/workbench.html").returncode, 0)
            malformed = Path(temp) / "bad.json"; malformed.write_text('{"schema_version":1,"inputs":[],"rules":[null]}')
            bad = run("evaluate", str(malformed), "--input", "fixtures/input.json", "--out", f"{temp}/bad-out.json")
            self.assertEqual(bad.returncode, 2)
            self.assertNotIn("Traceback", bad.stderr)


if __name__ == "__main__":
    unittest.main()
