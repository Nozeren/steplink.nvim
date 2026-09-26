import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from steplink.extractor import StepDefinition
from steplink.matcher import find_matches


def _step(decorator, pattern, function="f"):
    return StepDefinition(
        file=Path("x.py"), decorator=decorator, pattern=pattern, function=function,
        decorator_lineno=1, def_lineno=2,
    )


def test_unique_literal_match():
    steps = [_step("given", r"^I water every plant in the greenhouse$")]
    matches = find_matches(steps, "I water every plant in the greenhouse", "given")
    assert len(matches) == 1


def test_wrong_keyword_does_not_match():
    steps = [_step("when", r"^I water every plant in the greenhouse$")]
    matches = find_matches(steps, "I water every plant in the greenhouse", "given")
    assert matches == []


def test_step_decorator_matches_any_keyword():
    steps = [_step("step", r"^I open the \"Greenhouse\" page$")]
    for kw in ("given", "when", "then"):
        matches = find_matches(steps, 'I open the "Greenhouse" page', kw)
        assert len(matches) == 1


def test_no_match_returns_empty():
    steps = [_step("given", r"^something else$")]
    assert find_matches(steps, "I water every plant in the greenhouse", "given") == []


def test_does_not_falsely_match_a_similarly_shaped_pattern_with_a_fixed_literal_mismatch():
    # regression test: a naive "loosen every capture group" fallback made an unrelated
    # step (whose regex requires a completely different, fixed name) match too.
    # Matching must stay a strict literal re.match - placeholder resolution belongs
    # upstream (see outline.py), not as guessing inside the matcher itself.
    steps = [
        _step(
            "given",
            r'^I have (?P<wanted_state>enabled|disabled) the sprinkler '
            r'\"Tomato bed\"$',
            function="toggle_tomato_sprinkler",
        ),
        _step(
            "given",
            r'^I have (?P<wanted_state>enabled|disabled) the sprinkler '
            r'\"(?P<bed>herb spiral|berry patch|pumpkin corner)\"$',
            function="toggle_sprinkler",
        ),
    ]
    step_text = 'I have enabled the sprinkler "Tomato bed"'
    matches = find_matches(steps, step_text, "given")
    assert [m.step.function for m in matches] == ["toggle_tomato_sprinkler"]
