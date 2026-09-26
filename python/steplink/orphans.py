"""Repo-wide scan for step definitions that no scenario resolves to - candidates for
dead code. Runs the same reachability + matching machinery as `find_scenarios.py`, once
per step definition found anywhere in the repo, instead of once for a single cursor
position.
"""
import os
from pathlib import Path

from steplink.extractor import extract_step_definitions
from steplink.find_scenarios import search_scenarios_for_step
from steplink.project import _PRUNE_DIRS


def find_all_step_definitions(repo_root: Path) -> list:
    """Every `StepDefinition` in the repo, found via a flat walk rather than enumerating
    projects first - `core/` has no `features/` sibling so `discover_projects` never
    finds it as a project, but it still holds step definitions that must be included.
    """
    repo_root = repo_root.resolve()
    definitions = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in _PRUNE_DIRS and not d.startswith(".")]
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            definitions.extend(extract_step_definitions(Path(dirpath) / filename))
    return definitions


def find_orphaned_steps(repo_root: Path, progress_callback=None) -> dict:
    """Return `{"checked": N, "orphans": [...]}` - every step definition whose
    `search_scenarios_for_step` result is empty.

    `progress_callback(checked, total)`, if given, is invoked after each definition is
    checked - a full-repo scan can take a while, so callers (e.g. the CLI) can surface
    progress without touching stdout.
    """
    repo_root = repo_root.resolve()
    definitions = find_all_step_definitions(repo_root)
    total = len(definitions)

    orphans = []
    for checked, target in enumerate(definitions, start=1):
        matches, _feature_files = search_scenarios_for_step(target, repo_root)
        if not matches:
            orphans.append(
                {
                    "file": str(target.file),
                    "line": target.def_lineno,
                    "function": target.function,
                    "decorator": target.decorator,
                    "pattern": target.pattern,
                }
            )
        if progress_callback is not None:
            progress_callback(checked, total)

    return {"checked": total, "orphans": orphans}
