"""Match a resolved Gherkin step (keyword + text) against extracted step definitions."""
import re
from dataclasses import dataclass


@dataclass
class MatchResult:
    step: object  # extractor.StepDefinition


def _keyword_matches(step_decorator: str, resolved_keyword: str) -> bool:
    return step_decorator == "step" or step_decorator == resolved_keyword


def find_matches(step_definitions, step_text: str, resolved_keyword: str):
    """Return a MatchResult for every step definition whose keyword and regex match
    `step_text`. `step_text` should already have any Scenario Outline <placeholder>
    tokens resolved to a concrete value (see outline.py) - matching here is a plain
    literal `re.match`, exactly mirroring how pytest-bdd itself resolves a step.
    """
    candidates = [s for s in step_definitions if _keyword_matches(s.decorator, resolved_keyword)]
    matches = []
    for step in candidates:
        try:
            if re.match(step.pattern, step_text):
                matches.append(MatchResult(step=step))
        except re.error:
            continue
    return matches
