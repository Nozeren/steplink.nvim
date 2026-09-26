import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from steplink.gherkin import parse_feature_file


def _write(tmp_path, content):
    path = tmp_path / "x.feature"
    path.write_text(textwrap.dedent(content).lstrip("\n"))
    return path


def test_resolves_and_but_to_nearest_preceding_real_keyword(tmp_path):
    path = _write(
        tmp_path,
        """
        Feature: f

            Scenario: s
                Given a thing
                And another thing
                When I act
                But not that
                Then a result
        """,
    )
    steps = parse_feature_file(path)
    assert [(s.keyword, s.text) for s in steps] == [
        ("given", "a thing"),
        ("given", "another thing"),
        ("when", "I act"),
        ("when", "not that"),
        ("then", "a result"),
    ]


def test_tracks_scenario_title_and_resets_across_scenarios(tmp_path):
    path = _write(
        tmp_path,
        """
        Feature: f

            Scenario: first scenario
                Given a thing

            Scenario: second scenario
                Given another thing
        """,
    )
    steps = parse_feature_file(path)
    assert [s.scenario for s in steps] == ["first scenario", "second scenario"]


def test_scenario_outline_title_tracked_too(tmp_path):
    path = _write(
        tmp_path,
        """
        Feature: f

            Scenario Outline: outline title
                Given I have <state> the thing

                Examples:
                    | state |
                    | on    |
        """,
    )
    steps = parse_feature_file(path)
    assert steps[0].scenario == "outline title"
    assert steps[0].text == "I have <state> the thing"


def test_dangling_and_with_no_predecessor_is_skipped(tmp_path):
    path = _write(
        tmp_path,
        """
        Feature: f

            Scenario: s
                And a dangling and-step
                Given a real one
        """,
    )
    steps = parse_feature_file(path)
    assert [(s.keyword, s.text) for s in steps] == [("given", "a real one")]


def test_table_rows_and_docstrings_are_not_mistaken_for_steps(tmp_path):
    path = _write(
        tmp_path,
        '''
        Feature: f

            Scenario: s
                Given a table:
                    | level_0  | level_1 |
                    | folder_A | doc_B   |
                Then some text
        ''',
    )
    steps = parse_feature_file(path)
    assert [(s.keyword, s.text) for s in steps] == [
        ("given", "a table:"),
        ("then", "some text"),
    ]


def test_missing_file_returns_empty(tmp_path):
    assert parse_feature_file(tmp_path / "does_not_exist.feature") == []
