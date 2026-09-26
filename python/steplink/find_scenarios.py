"""CLI entrypoint: from a pytest-bdd step definition, find every scenario step that
resolves to it - the reverse of resolver.py. Invoked the same way (`python -m
steplink.find_scenarios ...`, cwd set to this package's containing `python/` dir),
same "always exactly one JSON object on stdout" contract.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from steplink.extractor import extract_step_definitions
from steplink.gherkin import parse_feature_file
from steplink.outline import resolve_outline_placeholders_all_rows
from steplink.project import find_reachable_feature_files


def _select_step_under_cursor(step_file: Path, cursor_line: int):
    """The decorated function whose decorator is nearest-at-or-above `cursor_line` -
    lets the cursor be anywhere in the function's signature/body, not just exactly on
    the decorator line.
    """
    candidates = [d for d in extract_step_definitions(step_file) if d.decorator_lineno <= cursor_line]
    if not candidates:
        return None
    return max(candidates, key=lambda d: d.decorator_lineno)


def _keyword_matches(step_decorator: str, resolved_keyword: str) -> bool:
    return step_decorator == "step" or step_decorator == resolved_keyword


def search_scenarios_for_step(target, repo_root: Path):
    """Every scenario step across the repo that resolves to `target` (a `StepDefinition`).

    Shared by the single-step, cursor-driven `find_scenarios()` below and the repo-wide
    orphan scan in `orphans.py`, so a correctness fix made auditing one benefits both.
    """
    feature_files = find_reachable_feature_files(target.file, repo_root)

    matches = []
    for feature_file in feature_files:
        for step in parse_feature_file(feature_file):
            if not _keyword_matches(target.decorator, step.keyword):
                continue
            candidate_texts = resolve_outline_placeholders_all_rows(feature_file, step.line, step.text)
            try:
                is_match = any(re.match(target.pattern, text) for text in candidate_texts)
            except re.error:
                is_match = False
            if is_match:
                matches.append(
                    {
                        "file": str(feature_file),
                        "line": step.line,
                        "scenario": step.scenario,
                        "text": step.text,
                    }
                )
    return matches, feature_files


def find_scenarios(step_file: Path, cursor_line: int, repo_root: Path):
    target = _select_step_under_cursor(step_file, cursor_line)
    if target is None:
        return {
            "status": "error",
            "message": (
                f"no @given/@when/@then/@step decorator found at or above line "
                f"{cursor_line} in {step_file}"
            ),
        }

    matches, feature_files = search_scenarios_for_step(target, repo_root)

    if matches:
        return {"status": "found", "matches": matches}
    return {
        "status": "no_match",
        "searched_feature_file_count": len(feature_files),
        "step_function": target.function,
        "step_pattern": target.pattern,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="steplink.find_scenarios")
    parser.add_argument("--step-file", required=True)
    parser.add_argument("--cursor-line", required=True, type=int)
    parser.add_argument("--repo-root", required=True)
    args = parser.parse_args(argv)

    try:
        result = find_scenarios(Path(args.step_file), args.cursor_line, Path(args.repo_root))
    except Exception as exc:  # boundary guard: stdout must always be valid JSON
        result = {"status": "error", "message": f"{type(exc).__name__}: {exc}"}

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
