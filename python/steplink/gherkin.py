"""Parse a .feature file's Given/When/Then/And/But steps, server-side (the reverse
direction has to scan potentially hundreds of feature files at once, unlike the forward
direction where Neovim's own buffer/cursor already pins down a single step).
"""
import re
from dataclasses import dataclass

_KEYWORD_RE = re.compile(r"^\s*(Given|When|Then|And|But)\s+(.*\S)\s*$", re.IGNORECASE)
_SCENARIO_TITLE_RE = re.compile(
    r"^\s*(?:Scenario Outline|Scenario Template|Scenario)\s*:\s*(.*\S)?\s*$", re.IGNORECASE
)
_BOUNDARY_RE = re.compile(
    r"^\s*(Scenario Outline|Scenario Template|Scenario|Background|Feature)\s*:", re.IGNORECASE
)

_REAL_KEYWORDS = {"given", "when", "then"}


@dataclass
class ScenarioStep:
    file: object  # pathlib.Path
    line: int  # 1-indexed
    scenario: str
    keyword: str  # given | when | then (And/But already resolved)
    text: str


def parse_feature_file(path) -> list:
    """Return every resolvable step in `path` as a `ScenarioStep`. And/But lines are
    resolved to the nearest preceding Given/When/Then within the same scenario; an
    And/But with no such predecessor (malformed file) is silently skipped.
    """
    try:
        lines = path.read_text(errors="ignore").splitlines()
    except OSError:
        return []

    steps = []
    scenario_title = ""
    last_real_keyword = None

    for lineno, line in enumerate(lines, start=1):
        boundary = _BOUNDARY_RE.match(line)
        if boundary:
            title_match = _SCENARIO_TITLE_RE.match(line)
            scenario_title = title_match.group(1) or "" if title_match else ""
            last_real_keyword = None
            continue

        match = _KEYWORD_RE.match(line)
        if not match:
            continue

        keyword = match.group(1).lower()
        text = match.group(2)

        if keyword in _REAL_KEYWORDS:
            last_real_keyword = keyword
        elif last_real_keyword is None:
            continue  # And/But with no preceding real keyword in this scenario
        else:
            keyword = last_real_keyword

        steps.append(ScenarioStep(file=path, line=lineno, scenario=scenario_title, keyword=keyword, text=text))

    return steps
