"""CLI entrypoint: repo-wide scan for orphaned (never-matched) pytest-bdd step
definitions. Invoked as `python -m steplink.find_orphans ...`, same "always exactly
one JSON object on stdout" contract as the other CLIs - progress is written to stderr
instead, since a full scan can take a while and no other CLI in this plugin uses stderr.
"""
import argparse
import json
import sys
from pathlib import Path

from steplink.orphans import find_orphaned_steps


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="steplink.find_orphans")
    parser.add_argument("--repo-root", required=True)
    args = parser.parse_args(argv)

    def report_progress(checked, total):
        print(f"{checked}/{total}", file=sys.stderr, flush=True)

    try:
        result = find_orphaned_steps(Path(args.repo_root), progress_callback=report_progress)
        result = {"status": "ok", **result}
    except Exception as exc:  # boundary guard: stdout must always be valid JSON
        result = {"status": "error", "message": f"{type(exc).__name__}: {exc}"}

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
