from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from . import __version__
from .core import ModelError, compare_models, evaluate, export_confirmed, render_html, replay, validate_model


def read_json(path: str) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ModelError(f"cannot read JSON file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ModelError(f"{path} must contain a JSON object")
    return value


def write(path: str, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=target.parent, prefix=f".{target.name}.", delete=False) as stream:
        temp = Path(stream.name)
        stream.write(content)
    try:
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)


def dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _input_files(args: argparse.Namespace) -> list[str]:
    if args.command == "evaluate":
        return [args.model, args.input]
    if args.command in {"replay", "export"}:
        return [args.model, args.cases]
    if args.command == "compare":
        return [args.old_model, args.new_model, args.cases]
    if args.command == "build":
        return [args.model]
    return []


def _guard_output(path: str, inputs: list[str]) -> None:
    output = Path(path).resolve()
    for input_path in inputs:
        if output == Path(input_path).resolve():
            raise ModelError(f"refusing to overwrite input file {input_path}; choose a different --out path")


def parser_for() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m intent_workbench", description="Evaluate a bounded, reviewed decision table.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("model")
    evaluate_cmd = commands.add_parser("evaluate")
    evaluate_cmd.add_argument("model")
    evaluate_cmd.add_argument("--input", required=True)
    evaluate_cmd.add_argument("--out", required=True)
    replay_cmd = commands.add_parser("replay")
    replay_cmd.add_argument("model")
    replay_cmd.add_argument("cases")
    replay_cmd.add_argument("--out", required=True)
    compare_cmd = commands.add_parser("compare")
    compare_cmd.add_argument("old_model")
    compare_cmd.add_argument("new_model")
    compare_cmd.add_argument("cases")
    compare_cmd.add_argument("--out", required=True)
    export_cmd = commands.add_parser("export")
    export_cmd.add_argument("model")
    export_cmd.add_argument("cases")
    export_cmd.add_argument("--out", required=True)
    build_cmd = commands.add_parser("build")
    build_cmd.add_argument("model")
    build_cmd.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = parser_for().parse_args(argv)
    try:
        if args.command == "validate":
            model = read_json(args.model)
            validate_model(model)
            drafts = [r["id"] for r in model["rules"] if r["review_status"] != "confirmed"]
            print(f"Valid model: {model['id']} revision {model['revision']} ({len(model['rules'])} rules, {len(drafts)} draft)")
            return 0
        if args.command == "evaluate":
            model, input_data = read_json(args.model), read_json(args.input)
            _guard_output(args.out, _input_files(args))
            # The object envelope is unambiguous only when its value is itself
            # a mapping. Scalar-valued `inputs` remains an ordinary input name.
            inputs = input_data["inputs"] if set(input_data) == {"inputs"} and isinstance(input_data["inputs"], dict) else input_data
            result = evaluate(model, inputs)
            write(args.out, dump(result))
            return 1 if result["status"] in {"missing", "conflict", "unresolved"} else 0
        if args.command == "replay":
            model, cases = read_json(args.model), read_json(args.cases)
            _guard_output(args.out, _input_files(args))
            result = replay(model, cases)
            write(args.out, dump(result))
            return 1 if any(row["comparison"] in {"mismatch", "not_scored"} and row["expectation_status"] == "confirmed" for row in result["cases"]) or any(row["prediction"]["status"] != "resolved" for row in result["cases"]) else 0
        if args.command == "compare":
            old_model, new_model, cases = read_json(args.old_model), read_json(args.new_model), read_json(args.cases)
            _guard_output(args.out, _input_files(args))
            result = compare_models(old_model, new_model, cases)
            write(args.out, dump(result))
            return 0
        if args.command == "export":
            model, cases = read_json(args.model), read_json(args.cases)
            _guard_output(args.out, _input_files(args))
            result = export_confirmed(model, cases)
            write(args.out, dump(result))
            return 0
        if args.command == "build":
            model = read_json(args.model)
            _guard_output(args.out, _input_files(args))
            result = render_html(model)
            write(args.out, result)
            print(f"Built offline workbench: {args.out}")
            return 0
    except ModelError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (OSError, UnicodeError) as exc:
        print(f"error: cannot write requested output: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
