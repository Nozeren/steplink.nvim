import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

import pytest
from steplink.find_scenarios import find_scenarios


def _touch(path: Path, content: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


@pytest.fixture
def repo(tmp_path):
    root = tmp_path
    _touch(
        root / "proj/conftest.py",
        "from .steps.common.plants import *\n",
    )
    _touch(
        root / "proj/steps/common/plants.py",
        "@given(re(r'^I have (?P<state>enabled|disabled) the thing$'))\n"
        "def edit_thing(state): pass\n"
        "\n"
        "@then(re(r'^unrelated step$'))\n"
        "def unrelated(): pass\n",
    )
    _touch(
        root / "proj/features/outline.feature",
        "Feature: f\n\n"
        "    Scenario Outline: s\n"
        '        Given I have <state> the thing\n'
        "\n"
        "        Examples:\n"
        "            | state    |\n"
        "            | enabled  |\n"
        "            | disabled |\n",
    )
    _touch(
        root / "proj/features/plain.feature",
        "Feature: f2\n\n"
        "    Scenario: plain\n"
        "        Given I have enabled the thing\n",
    )
    return root


def test_finds_scenarios_across_multiple_examples_rows_and_files(repo):
    result = find_scenarios(repo / "proj/steps/common/plants.py", 1, repo)
    assert result["status"] == "found"
    files = {(m["file"], m["line"]) for m in result["matches"]}
    assert (str(repo / "proj/features/outline.feature"), 4) in files
    assert (str(repo / "proj/features/plain.feature"), 4) in files


def test_cursor_selects_the_nearest_preceding_decorator(repo):
    # cursor line 4 is inside unrelated()'s body, decorator at line 4... use the actual
    # decorator line for `unrelated` (line 4 in the file) to target it specifically
    result = find_scenarios(repo / "proj/steps/common/plants.py", 5, repo)
    assert result["status"] == "no_match"
    assert result["step_function"] == "unrelated"


def test_no_decorator_above_cursor_is_an_error(repo):
    result = find_scenarios(repo / "proj/steps/common/plants.py", 0, repo)
    assert result["status"] == "error"


def test_no_match_reports_searched_file_count(repo):
    _touch(
        root_conftest := repo / "proj/steps/nomatch/conftest.py",
        "@given(re(r'^a step nobody uses$'))\ndef nobody(): pass\n",
    )
    # a feature file that IS in the conftest's reachable subtree, so the search has at
    # least one real file to look through (and correctly finds no match in it)
    _touch(
        repo / "proj/features/nomatch/other.feature",
        "Feature: f\n\n  Scenario: s\n    Given something unrelated\n",
    )
    result = find_scenarios(root_conftest, 1, repo)
    assert result["status"] == "no_match"
    assert result["searched_feature_file_count"] >= 1
