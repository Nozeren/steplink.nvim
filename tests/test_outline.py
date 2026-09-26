import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from steplink.outline import resolve_outline_placeholders, resolve_outline_placeholders_all_rows


def _write_feature(tmp_path, content):
    path = tmp_path / "outline.feature"
    path.write_text(textwrap.dedent(content).lstrip("\n"))
    return path


def test_no_placeholder_is_a_noop(tmp_path):
    path = _write_feature(tmp_path, "Feature: f\n  Scenario: s\n    Given a plain step\n")
    result = resolve_outline_placeholders(path, 3, "a plain step")
    assert result.resolved_text == "a plain step"
    assert result.substituted is False


def test_resolves_from_the_first_examples_row(tmp_path):
    content = """
    Feature: f

        Scenario Outline: s
            Given I have <sprinkler_state> the sprinkler "Tomato bed"

            Examples:
                | sprinkler_state |
                | enabled         |
                | disabled        |
    """
    path = _write_feature(tmp_path, content)
    step_line = 4  # 1-indexed line of the Given step
    result = resolve_outline_placeholders(
        path, step_line, 'I have <sprinkler_state> the sprinkler "Tomato bed"'
    )
    assert result.substituted is True
    assert result.resolved_text == 'I have enabled the sprinkler "Tomato bed"'


def test_multiple_placeholders_in_one_step(tmp_path):
    content = """
    Feature: f

        Scenario Outline: s
            Given I water <plant> with <amount>

            Examples:
                | plant | amount |
                | Basil | 1 cup  |
    """
    path = _write_feature(tmp_path, content)
    result = resolve_outline_placeholders(path, 4, "I water <plant> with <amount>")
    assert result.resolved_text == "I water Basil with 1 cup"


def test_stops_at_next_scenario_boundary_without_finding_examples(tmp_path):
    content = """
    Feature: f

        Scenario Outline: s
            Given I have <sprinkler_state> the sprinkler "X"

        Scenario: other
            Given something else

        Examples:
            | sprinkler_state |
            | enabled         |
    """
    path = _write_feature(tmp_path, content)
    result = resolve_outline_placeholders(path, 4, 'I have <sprinkler_state> the sprinkler "X"')
    assert result.substituted is False
    assert result.resolved_text == 'I have <sprinkler_state> the sprinkler "X"'


def test_no_examples_table_at_all_leaves_text_unchanged(tmp_path):
    path = _write_feature(tmp_path, "Feature: f\n  Scenario Outline: s\n    Given I have <x>\n")
    result = resolve_outline_placeholders(path, 3, "I have <x>")
    assert result.substituted is False


def test_unknown_placeholder_name_left_as_is(tmp_path):
    content = """
    Feature: f

        Scenario Outline: s
            Given I have <unknown_name>

            Examples:
                | sprinkler_state |
                | enabled         |
    """
    path = _write_feature(tmp_path, content)
    result = resolve_outline_placeholders(path, 4, "I have <unknown_name>")
    assert result.resolved_text == "I have <unknown_name>"


def test_all_rows_returns_one_resolved_text_per_examples_row(tmp_path):
    content = """
    Feature: f

        Scenario Outline: s
            Given I have <sprinkler_state> the sprinkler "Tomato bed"

            Examples:
                | sprinkler_state |
                | enabled         |
                | disabled        |
    """
    path = _write_feature(tmp_path, content)
    results = resolve_outline_placeholders_all_rows(
        path, 4, 'I have <sprinkler_state> the sprinkler "Tomato bed"'
    )
    assert results == [
        'I have enabled the sprinkler "Tomato bed"',
        'I have disabled the sprinkler "Tomato bed"',
    ]


def test_all_rows_no_placeholder_returns_single_item_list(tmp_path):
    path = _write_feature(tmp_path, "Feature: f\n  Scenario: s\n    Given a plain step\n")
    assert resolve_outline_placeholders_all_rows(path, 3, "a plain step") == ["a plain step"]


def test_all_rows_no_examples_table_returns_original_text_only(tmp_path):
    path = _write_feature(tmp_path, "Feature: f\n  Scenario Outline: s\n    Given I have <x>\n")
    assert resolve_outline_placeholders_all_rows(path, 3, "I have <x>") == ["I have <x>"]
