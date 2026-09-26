"""Resolve which .py files can define the step behind a given feature-file step.

Two distinct pytest mechanisms make a step definition visible to a given feature file,
and both must be modeled:

1. Ancestor conftest.py auto-loading: pytest automatically loads every conftest.py that
   is a filesystem ancestor of a test file. Feature files live in a directory tree that
   mirrors the steps tree (e.g. bdd/features/x/y <-> bdd/steps/x/y), so this is modeled
   by mirroring the feature file's directory into the steps tree and walking up to the
   project's steps root, collecting conftest.py files along the way - exactly what
   pytest itself would auto-load.

2. Explicit cross-tree imports: shared steps in a top-level core/ sit outside every BDD
   project's own directory tree, so pytest's ancestor-based auto-loading never reaches
   them. Each project's root conftest.py (e.g. bdd/conftest.py) explicitly bridges this
   with `from X import *` statements - both absolute (`from core.steps.common.plants
   import *`) and project-relative (`from .steps.common.plants import *`,
   `from .steps.tools.helpers import *`). Importing a module executes it, which is what
   actually registers its pytest-bdd step decorators - so any module reachable via a
   star-import chain from the project's (or repo's) root conftest.py is just as visible
   project-wide as if pytest had auto-loaded it. This is resolved by parsing those
   conftest.py files with ast and following `import *` targets to a fixed point.
"""
import ast
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

_PRUNE_DIRS = {
    ".venv", ".git", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
    "logs", "reports", ".specify",
}


class ProjectResolutionError(Exception):
    """Raised when a feature file isn't under a discoverable BDD project."""


@dataclass
class CandidateFiles:
    project_root: Path
    features_root: Path
    mirror_dir: Path
    conftest_files: list = field(default_factory=list)  # deepest-first, ancestor-scoped
    local_test_files: list = field(default_factory=list)
    project_wide_files: list = field(default_factory=list)  # star-import-resolved, repo/project root

    @property
    def all_files(self):
        seen = set()
        ordered = []
        for f in (*self.project_wide_files, *self.conftest_files, *self.local_test_files):
            if f not in seen:
                seen.add(f)
                ordered.append(f)
        return ordered


def _find_features_root(feature_file: Path) -> Path:
    for parent in feature_file.parents:
        if parent.name == "features":
            return parent
    raise ProjectResolutionError(
        f"no ancestor directory named 'features' found above {feature_file}"
    )


def _collect_ancestor_conftests(mirror_dir: Path, steps_root: Path) -> list:
    candidates = [mirror_dir, *mirror_dir.parents]
    conftests = []
    for directory in candidates:
        try:
            directory.relative_to(steps_root)
        except ValueError:
            if directory != steps_root:
                break
        conftest = directory / "conftest.py"
        if conftest.is_file():
            conftests.append(conftest)
        if directory == steps_root:
            break
    return conftests


def _star_imported_targets(path: Path):
    """Yield (level, dotted_module_or_None) for every `from X import *` in `path`."""
    try:
        tree = ast.parse(path.read_text(errors="ignore"), filename=str(path))
    except (SyntaxError, OSError):
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if len(node.names) == 1 and node.names[0].name == "*":
            yield node.level, node.module


def _resolve_import_target(source_file: Path, level: int, module, repo_root: Path):
    if level == 0:
        # absolute import (e.g. `from core.steps.common.plants import *`), resolved
        # relative to the repo root, same as Python would via sys.path
        base_dir = repo_root
    else:
        # relative import (e.g. `from .steps.common.plants import *`), resolved
        # relative to the importing file's own package directory
        base_dir = source_file.parent
        for _ in range(level - 1):
            base_dir = base_dir.parent
    target = base_dir / Path(*module.split(".")) if module else base_dir

    as_module = target.with_suffix(".py")
    if as_module.is_file():
        return as_module
    as_package = target / "__init__.py"
    if as_package.is_file():
        return as_package
    return None


def _resolve_star_imports_transitively(entry_files, repo_root: Path) -> list:
    """Starting from `entry_files`, follow `import *` chains to a fixed point.

    Returns the entry files plus every transitively star-imported .py file, in
    discovery order. Entry files are included even though they typically hold no
    decorators themselves, since it's harmless (extractor finds nothing) and keeps
    this function's contract simple: "everything reachable, including the roots."
    """
    visited = set()
    queue = list(entry_files)
    resolved = []
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        if not current.is_file():
            continue
        resolved.append(current)
        for level, module in _star_imported_targets(current):
            target = _resolve_import_target(current, level, module, repo_root)
            if target is not None and target not in visited:
                queue.append(target)
    return resolved


def resolve_candidate_files(feature_file: Path, repo_root: Path) -> CandidateFiles:
    feature_file = feature_file.resolve()
    repo_root = repo_root.resolve()

    features_root = _find_features_root(feature_file)
    project_root = features_root.parent
    steps_root = project_root / "steps"
    if not steps_root.is_dir():
        raise ProjectResolutionError(
            f"expected a sibling 'steps' directory at {steps_root}, but it doesn't exist"
        )

    relative_dir = feature_file.parent.relative_to(features_root)
    mirror_dir = steps_root / relative_dir

    conftest_files = _collect_ancestor_conftests(mirror_dir, steps_root)
    local_test_files = sorted(mirror_dir.glob("test_*.py")) if mirror_dir.is_dir() else []

    # Any ancestor conftest.py - not just the project's root one - can star-import a
    # sibling directory (e.g. bdd/steps/harvest/conftest.py does
    # `from .common.baskets import *`, where common/ is a sibling of summer/
    # and winter/, not an ancestor). Every ancestor conftest.py is a legitimate entry
    # point for this resolution, since pytest would auto-load it and execute its
    # imports regardless of what else it star-imports.
    entry_points = list(conftest_files)
    repo_conftest = repo_root / "conftest.py"
    if repo_conftest.is_file() and repo_conftest not in entry_points:
        entry_points.append(repo_conftest)
    project_conftest = project_root / "conftest.py"
    if project_conftest.is_file() and project_conftest not in entry_points:
        entry_points.append(project_conftest)
    project_wide_files = _resolve_star_imports_transitively(entry_points, repo_root)

    return CandidateFiles(
        project_root=project_root,
        features_root=features_root,
        mirror_dir=mirror_dir,
        conftest_files=conftest_files,
        local_test_files=local_test_files,
        project_wide_files=project_wide_files,
    )


def discover_projects(repo_root: Path) -> list:
    """Find every BDD project root in the repo - a directory with sibling `features/`
    and `steps/` directories. Same detection rule as `_find_features_root`, just run in
    the other direction (enumerate all of them instead of finding one ancestor).
    """
    repo_root = repo_root.resolve()
    projects = []
    for dirpath, dirnames, _ in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in _PRUNE_DIRS and not d.startswith(".")]
        if os.path.basename(dirpath) == "features":
            project_root = Path(dirpath).parent
            if (project_root / "steps").is_dir():
                projects.append(project_root)
    return sorted(set(projects))


def _feature_files_bound_by_scenarios(test_file: Path) -> list:
    """Parse `scenarios(...)` calls in a test_*.py file, resolving each relative feature
    path against the file's own directory - the exact feature file(s) this file's
    directly-defined steps are visible to (pytest fixture scoping is per-module for a
    test_*.py's own fixtures, unlike conftest.py's directory-wide scope).
    """
    try:
        tree = ast.parse(test_file.read_text(errors="ignore"), filename=str(test_file))
    except (SyntaxError, OSError):
        return []
    results = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name != "scenarios":
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                resolved = (test_file.parent / arg.value).resolve()
                if resolved.is_file():
                    results.append(resolved)
    return results


def _project_conftest_files(project_root: Path) -> list:
    files = []
    root_conftest = project_root / "conftest.py"
    if root_conftest.is_file():
        files.append(root_conftest)
    steps_root = project_root / "steps"
    if steps_root.is_dir():
        files.extend(sorted(steps_root.rglob("conftest.py")))
    return files


def _mirror_steps_dir_to_features(steps_dir: Path, project_root: Path) -> Path:
    relative = steps_dir.relative_to(project_root / "steps")
    return project_root / "features" / relative


@lru_cache(maxsize=None)
def _cached_star_import_closure(conftest: Path, repo_root: Path) -> tuple:
    """`_resolve_star_imports_transitively([conftest], repo_root)`, memoized.

    The closure depends only on `conftest` and `repo_root`, never on the step file being
    searched for - `find_reachable_feature_files` below calls this once per (conftest,
    candidate step definition) pair, so across a repo-wide scan of hundreds of step
    definitions the same conftest's closure would otherwise be recomputed from scratch
    every time. Safe to cache for the process lifetime of a one-shot CLI invocation.
    """
    return tuple(_resolve_star_imports_transitively([conftest], repo_root))


def find_reachable_feature_files(step_file: Path, repo_root: Path) -> list:
    """Reverse of `resolve_candidate_files`: given a Python step-definition file, find
    every .feature file whose own candidate set would include it.
    """
    step_file = step_file.resolve()
    repo_root = repo_root.resolve()

    if step_file.name.startswith("test_") and step_file.suffix == ".py":
        bound = _feature_files_bound_by_scenarios(step_file)
        if bound:
            return sorted(set(bound))
        # a test_*.py with no scenarios() call is unusual, but falls through to the
        # general star-import search below rather than returning nothing

    core_root = repo_root / "core"
    try:
        step_file.relative_to(core_root)
        candidate_projects = discover_projects(repo_root)
    except ValueError:
        steps_dir = next((p for p in step_file.parents if p.name == "steps"), None)
        if steps_dir is None:
            return []
        candidate_projects = [steps_dir.parent]

    reachable_features = []
    seen_dirs = set()
    for project_root in candidate_projects:
        features_root = project_root / "features"
        if not features_root.is_dir() or not (project_root / "steps").is_dir():
            continue
        for conftest in _project_conftest_files(project_root):
            reaches = conftest == step_file or step_file in _cached_star_import_closure(
                conftest, repo_root
            )
            if not reaches:
                continue
            if conftest.parent == project_root:
                mirror_features_dir = features_root
            else:
                mirror_features_dir = _mirror_steps_dir_to_features(conftest.parent, project_root)
            if mirror_features_dir in seen_dirs:
                continue
            seen_dirs.add(mirror_features_dir)
            if mirror_features_dir.is_dir():
                reachable_features.extend(mirror_features_dir.rglob("*.feature"))

    return sorted(set(reachable_features))
