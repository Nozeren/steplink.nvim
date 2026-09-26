import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from steplink.extractor import extract_step_definitions


def _write(tmp_path, content):
    path = tmp_path / "conftest.py"
    path.write_text(textwrap.dedent(content))
    return path


def test_extracts_given_when_then_and_step(tmp_path):
    path = _write(
        tmp_path,
        '''
        from pytest_bdd import given, when, then, step
        from pytest_bdd.parsers import re

        @given(re(r"^I do a thing$"))
        def do_thing():
            pass

        @when(re(r"^I click the \\"(?P<action>Water|Skip)\\" button$"))
        def click_button(action):
            pass

        @then(re(r"^the thing is done$"), target_fixture="result")
        def thing_is_done():
            pass

        @step(re(r"^a wildcard step$"))
        def wildcard_step():
            pass
        ''',
    )
    defs = extract_step_definitions(path)
    by_function = {d.function: d for d in defs}

    assert by_function["do_thing"].decorator == "given"
    assert by_function["do_thing"].pattern == "^I do a thing$"

    assert by_function["click_button"].decorator == "when"
    assert "(?P<action>Water|Skip)" in by_function["click_button"].pattern

    assert by_function["thing_is_done"].decorator == "then"

    assert by_function["wildcard_step"].decorator == "step"


def test_def_lineno_is_the_def_line_not_the_decorator_line(tmp_path):
    path = _write(
        tmp_path,
        '''
        @given(re(r"^step one$"))
        def step_one():
            pass
        ''',
    )
    defs = extract_step_definitions(path)
    assert defs[0].decorator_lineno == 2
    assert defs[0].def_lineno == 3


def test_skips_non_string_patterns_without_crashing(tmp_path):
    path = _write(
        tmp_path,
        '''
        PATTERN = r"^dynamic$"

        @given(re(PATTERN))
        def dynamic_step():
            pass

        @given(re(r"^static$"))
        def static_step():
            pass
        ''',
    )
    defs = extract_step_definitions(path)
    assert [d.function for d in defs] == ["static_step"]


def test_missing_file_returns_empty(tmp_path):
    assert extract_step_definitions(tmp_path / "does_not_exist.py") == []
