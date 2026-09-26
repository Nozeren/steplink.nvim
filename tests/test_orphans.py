import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

import pytest
from steplink.orphans import find_all_step_definitions, find_orphaned_steps


def _touch(path: Path, content: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


@pytest.fixture
def repo(tmp_path):
    root = tmp_path

    _touch(root / "proj/conftest.py", "from .steps.common.plants import *\n")
    _touch(
        root / "proj/steps/common/plants.py",
        "@given(re(r'^I have (?P<state>enabled|disabled) the thing$'))\n"
        "def used_via_outline(state): pass\n"
        "\n"
        "@then(re(r'^a step nobody uses$'))\n"
        "def truly_orphaned(): pass\n",
    )
    _touch(
        root / "proj/features/outline.feature",
        "Feature: f\n\n"
        "    Scenario Outline: s\n"
        "        Given I have <state> the thing\n"
        "\n"
        "        Examples:\n"
        "            | state    |\n"
        "            | enabled  |\n"
        "            | disabled |\n",
    )

    # a step only reachable via an ancestor conftest.py's star-import of a sibling dir
    _touch(root / "proj/steps/harvest/conftest.py", "from .common.baskets import *\n")
    _touch(
        root / "proj/steps/harvest/common/baskets.py",
        "@then(re(r'^shared harvest step$'))\ndef used_via_star_import(): pass\n",
    )
    _touch(
        root / "proj/features/harvest/leaf.feature",
        "Feature: f\n\n  Scenario: s\n    Then shared harvest step\n",
    )

    # core/ has no features/ of its own and nothing star-imports it in this fixture -
    # discover_projects() would never find it, but a full-repo walk must still catch it
    _touch(
        root / "core/steps/common/auth.py",
        "@given(re(r'^an unused core step$'))\ndef unused_core(): pass\n",
    )

    return root


def test_find_all_step_definitions_includes_core_even_without_its_own_project(repo):
    functions = {d.function for d in find_all_step_definitions(repo)}
    assert functions == {"used_via_outline", "truly_orphaned", "used_via_star_import", "unused_core"}


def test_find_orphaned_steps_flags_only_genuinely_unused_definitions(repo):
    result = find_orphaned_steps(repo)
    assert result["checked"] == 4
    orphan_functions = {o["function"] for o in result["orphans"]}
    assert orphan_functions == {"truly_orphaned", "unused_core"}


def test_find_orphaned_steps_reports_progress(repo):
    calls = []
    find_orphaned_steps(repo, progress_callback=lambda checked, total: calls.append((checked, total)))
    assert calls[-1] == (4, 4)
    assert [c for c, _ in calls] == [1, 2, 3, 4]
