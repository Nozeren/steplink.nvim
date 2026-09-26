"""CLI entrypoint: resolve a Gherkin step to its pytest-bdd step definition.

Invoked as `python -m steplink.resolver ...` with cwd set to this package's
containing `python/` directory (Python's -m adds cwd to sys.path automatically).
Always prints exactly one JSON object to stdout - callers (the Neovim Lua bridge, or
a human debugging from a shell) can rely on that contract regardless of outcome.
"""
import argparse
import json
import sys
from pathlib import Path

from steplink.extractor import extract_step_definitions
from steplink.matcher import find_matches
from steplink.outline import resolve_outline_placeholders
from steplink.project import ProjectResolutionError, resolve_candidate_files


def _match_payload(step):
    return {
        "file": str(step.file),
        "line": step.def_lineno,
        "decorator_line": step.decorator_lineno,
        "function": step.function,
        "pattern": step.pattern,
        "decorator": step.decorator,
    }


def resolve(feature_file: Path, repo_root: Path, step_text: str, keyword: str, step_line: int):
    try:
        candidates = resolve_candidate_files(feature_file, repo_root)
    except ProjectResolutionError as exc:
        return {"status": "error", "message": str(exc)}

    step_definitions = []
    for path in candidates.all_files:
        step_definitions.extend(extract_step_definitions(path))

    outline = resolve_outline_placeholders(feature_file, step_line, step_text)
    matches = find_matches(step_definitions, outline.resolved_text, keyword)

    if len(matches) == 1:
        return {"status": "match", "match": _match_payload(matches[0].step)}
    if len(matches) > 1:
        return {"status": "ambiguous", "matches": [_match_payload(m.step) for m in matches]}
    return {
        "status": "no_match",
        "reason": "no candidate decorator matched the step text",
        "resolved_step_text": outline.resolved_text,
        "searched_files": [str(path) for path in candidates.all_files],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="steplink.resolver")
    parser.add_argument("--feature-file", required=True)
    parser.add_argument("--step-text", required=True)
    parser.add_argument("--keyword", required=True, choices=["given", "when", "then"])
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--step-line", required=True, type=int)
    args = parser.parse_args(argv)

    try:
        result = resolve(
            Path(args.feature_file),
            Path(args.repo_root),
            args.step_text,
            args.keyword,
            args.step_line,
        )
    except Exception as exc:  # boundary guard: stdout must always be valid JSON
        result = {"status": "error", "message": f"{type(exc).__name__}: {exc}"}

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
