import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

import pytest
from steplink.project import (
    ProjectResolutionError,
    discover_projects,
    find_reachable_feature_files,
    resolve_candidate_files,
)


def _touch(path: Path, content: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


@pytest.fixture
def repo(tmp_path):
    root = tmp_path
    _touch(root / "core/steps/common/auth.py", "@given(re(r'^shared core step$'))\ndef f(): pass\n")

    _touch(
        root / "proj/conftest.py",
        "from core.steps.common.auth import *\n"
        "from .steps.common.plants import *\n"
        "from .steps.tools.helpers import *\n",
    )
    _touch(root / "proj/steps/common/plants.py", "@given(re(r'^shared project step$'))\ndef g(): pass\n")
    _touch(root / "proj/steps/tools/helpers.py", "@when(re(r'^a project-local helper step$'))\ndef h(): pass\n")

    _touch(root / "proj/features/root_level.feature")
    _touch(root / "proj/steps/conftest.py")

    _touch(root / "proj/features/a/b/c/leaf.feature")
    _touch(root / "proj/steps/a/conftest.py")
    _touch(root / "proj/steps/a/b/conftest.py")
    _touch(root / "proj/steps/a/b/c/conftest.py")
    _touch(root / "proj/steps/a/b/c/test_leaf.py")
    _touch(root / "proj/steps/a/x/conftest.py")  # sibling branch, must NOT be picked up

    # regression fixture: an intermediate ancestor
    # conftest.py (not the project root) star-imports a *sibling* directory
    _touch(root / "proj/steps/harvest/conftest.py", "from .common.baskets import *\n")
    _touch(
        root / "proj/steps/harvest/common/baskets.py",
        "@then(re(r'^shared harvest step$'))\ndef w(): pass\n",
    )
    _touch(root / "proj/features/harvest/summer/leaf.feature")

    # core/ has its own features/ dir too, so discover_projects() should find it as a
    # second, independent project (no conftest.py of its own in this fixture - it's
    # only ever reached *through* proj's star-imports)
    _touch(root / "core/features/core_own.feature")

    # a test_*.py that binds its own scenario precisely via scenarios(...) - reverse
    # lookup for this file must resolve to exactly that one feature file, not the whole
    # project tree
    _touch(
        root / "proj/steps/scenarios_dir/test_bound.py",
        "from pytest_bdd import scenarios\nscenarios('../../features/scenarios_dir/target.feature')\n"
        "@given(re(r'^a locally bound step$'))\ndef b(): pass\n",
    )
    _touch(root / "proj/features/scenarios_dir/target.feature")

    return root


def test_root_level_feature_file_mirrors_to_steps_root(repo):
    result = resolve_candidate_files(repo / "proj/features/root_level.feature", repo)
    assert result.mirror_dir == repo / "proj/steps"
    assert result.conftest_files == [repo / "proj/steps/conftest.py"]
    assert result.local_test_files == []


def test_nested_feature_collects_only_ancestor_conftests_deepest_first(repo):
    result = resolve_candidate_files(repo / "proj/features/a/b/c/leaf.feature", repo)
    assert result.conftest_files == [
        repo / "proj/steps/a/b/c/conftest.py",
        repo / "proj/steps/a/b/conftest.py",
        repo / "proj/steps/a/conftest.py",
        repo / "proj/steps/conftest.py",
    ]
    # sibling branch's conftest must not leak in
    assert (repo / "proj/steps/a/x/conftest.py") not in result.conftest_files
    assert result.local_test_files == [repo / "proj/steps/a/b/c/test_leaf.py"]


def test_project_root_conftest_star_imports_are_resolved_transitively(repo):
    result = resolve_candidate_files(repo / "proj/features/root_level.feature", repo)
    # both the project-local common module and the arbitrarily-named helper module
    # (star-imported by proj/conftest.py) must be pulled in, project-wide
    assert (repo / "proj/steps/common/plants.py") in result.project_wide_files
    assert (repo / "proj/steps/tools/helpers.py") in result.project_wide_files
    # and the absolute cross-tree import into core/ must resolve too
    assert (repo / "core/steps/common/auth.py") in result.project_wide_files


def test_project_wide_files_apply_regardless_of_feature_file_location(repo):
    # the whole point: a project-root star-import is visible to every feature in the
    # project, not just ones "under" the conftest.py that did the importing
    result = resolve_candidate_files(repo / "proj/features/a/b/c/leaf.feature", repo)
    assert (repo / "proj/steps/tools/helpers.py") in result.project_wide_files


def test_ancestor_conftest_star_import_reaches_sibling_directory(repo):
    # regression test: proj/steps/harvest/conftest.py does `from .common.baskets
    # import *`, where common/ is a SIBLING of summer/ and winter/, not an
    # ancestor of either. Any ancestor conftest.py - not just the project root's own -
    # must have its star-imports resolved, or steps like this are silently missed.
    result = resolve_candidate_files(repo / "proj/features/harvest/summer/leaf.feature", repo)
    assert (repo / "proj/steps/harvest/conftest.py") in result.conftest_files
    assert (repo / "proj/steps/harvest/common/baskets.py") in result.project_wide_files


def test_missing_features_ancestor_raises(tmp_path):
    stray = _touch(tmp_path / "somewhere/else/leaf.feature")
    with pytest.raises(ProjectResolutionError):
        resolve_candidate_files(stray, tmp_path)


def test_missing_sibling_steps_dir_raises(tmp_path):
    feature = _touch(tmp_path / "proj/features/leaf.feature")
    with pytest.raises(ProjectResolutionError):
        resolve_candidate_files(feature, tmp_path)


def test_discover_projects_finds_every_project_and_nothing_else(repo):
    projects = discover_projects(repo)
    assert set(projects) == {repo / "proj", repo / "core"}


def test_discover_projects_ignores_features_dir_without_sibling_steps(tmp_path):
    _touch(tmp_path / "incomplete/features/x.feature")
    assert discover_projects(tmp_path) == []


def test_reachable_features_for_ancestor_conftest_is_just_its_own_subtree(repo):
    files = find_reachable_feature_files(repo / "proj/steps/a/b/c/conftest.py", repo)
    assert files == [repo / "proj/features/a/b/c/leaf.feature"]


def test_reachable_features_for_project_root_star_import_is_the_whole_tree(repo):
    # proj/steps/common/plants.py is star-imported by proj/conftest.py (the project
    # root) - reachable from every feature file in the project, not just some subtree
    files = find_reachable_feature_files(repo / "proj/steps/common/plants.py", repo)
    assert repo / "proj/features/root_level.feature" in files
    assert repo / "proj/features/a/b/c/leaf.feature" in files
    assert repo / "proj/features/harvest/summer/leaf.feature" in files


def test_reachable_features_for_sibling_star_import_is_scoped_to_its_subtree(repo):
    # regression test, the reverse direction of the one above: a leaf module
    # star-imported by an *intermediate* ancestor conftest.py (not the project root)
    # must only be reachable from that conftest's own subtree, not the whole project
    files = find_reachable_feature_files(repo / "proj/steps/harvest/common/baskets.py", repo)
    assert files == [repo / "proj/features/harvest/summer/leaf.feature"]


def test_reachable_features_for_test_file_is_exactly_its_own_scenarios_binding(repo):
    files = find_reachable_feature_files(repo / "proj/steps/scenarios_dir/test_bound.py", repo)
    assert files == [repo / "proj/features/scenarios_dir/target.feature"]


def test_reachable_features_for_orphaned_test_file_is_empty(repo):
    # proj/steps/a/b/c/test_leaf.py has no scenarios() call and isn't star-imported by
    # anything - it shouldn't falsely claim reachability from anywhere
    files = find_reachable_feature_files(repo / "proj/steps/a/b/c/test_leaf.py", repo)
    assert files == []


def test_reachable_features_for_core_file_is_found_via_importing_project(repo):
    # core/steps/common/auth.py has no conftest.py of its own in this fixture - it's
    # only reachable because proj/conftest.py absolute-imports it
    files = find_reachable_feature_files(repo / "core/steps/common/auth.py", repo)
    assert repo / "proj/features/root_level.feature" in files
