"""Resolve Scenario Outline <placeholder> tokens to a concrete value from the nearest
Examples: table, the same substitution pytest-bdd performs at runtime before matching
a step against its regex. Reading the raw .feature file text is necessary here because
an unresolved placeholder (e.g. <sprinkler_state>) won't satisfy a step definition's
regex/alternation literally, and its concrete values live in a table elsewhere in the
same scenario, not in the step line itself.
"""
import re
from dataclasses import dataclass

PLACEHOLDER_RE = re.compile(r"<([^<>]+)>")
_SCENARIO_BOUNDARY_RE = re.compile(
    r"^\s*(Scenario Outline|Scenario Template|Scenario|Background|Feature)\s*:", re.IGNORECASE
)
_EXAMPLES_RE = re.compile(r"^\s*(Examples|Scenarios)\s*:", re.IGNORECASE)
_TABLE_ROW_RE = re.compile(r"^\s*\|(.*)\|\s*$")


@dataclass
class OutlineResolution:
    resolved_text: str
    substituted: bool  # True if at least one <placeholder> was replaced


def _parse_table_row(line: str):
    match = _TABLE_ROW_RE.match(line)
    if not match:
        return None
    return [cell.strip() for cell in match.group(1).split("|")]


def _find_examples_rows(lines, start_index: int):
    """Scan forward from `start_index` (0-based, the step's own line) for this
    scenario's Examples: table. Stops at the next Scenario/Feature boundary without
    finding one. Returns (header_row, [data_row, ...]) or None.
    """
    i = start_index + 1
    n = len(lines)
    while i < n and not _EXAMPLES_RE.match(lines[i]):
        if _SCENARIO_BOUNDARY_RE.match(lines[i]):
            return None
        i += 1
    if i >= n:
        return None

    i += 1  # move past the "Examples:" line itself
    rows = []
    while i < n:
        row = _parse_table_row(lines[i])
        if row is None:
            break
        rows.append(row)
        i += 1

    if len(rows) < 2:
        return None
    return rows[0], rows[1:]


def _substitute_row(step_text: str, header, row) -> str:
    if len(header) != len(row):
        return step_text
    values = dict(zip(header, row))

    def _substitute(match):
        return values.get(match.group(1), match.group(0))

    return PLACEHOLDER_RE.sub(_substitute, step_text)


def resolve_outline_placeholders(feature_file, step_line: int, step_text: str) -> OutlineResolution:
    """`step_line` is the 1-indexed line number of the step within `feature_file`.
    Resolves against the *first* Examples: row only - sufficient for the forward
    direction, where the caller already has one concrete step instance in hand.
    """
    if not PLACEHOLDER_RE.search(step_text):
        return OutlineResolution(resolved_text=step_text, substituted=False)

    try:
        lines = feature_file.read_text(errors="ignore").splitlines()
    except OSError:
        return OutlineResolution(resolved_text=step_text, substituted=False)

    table = _find_examples_rows(lines, step_line - 1)
    if table is None:
        return OutlineResolution(resolved_text=step_text, substituted=False)

    header, data_rows = table
    resolved = _substitute_row(step_text, header, data_rows[0])
    return OutlineResolution(resolved_text=resolved, substituted=resolved != step_text)


def resolve_outline_placeholders_all_rows(feature_file, step_line: int, step_text: str) -> list:
    """Like `resolve_outline_placeholders`, but returns one resolved string per
    Examples: row instead of just the first - used by the reverse (step -> scenarios)
    lookup, where missing a match because a *different* row's value was needed would be
    a false negative, unlike the forward direction which only ever needs one instance.
    """
    if not PLACEHOLDER_RE.search(step_text):
        return [step_text]

    try:
        lines = feature_file.read_text(errors="ignore").splitlines()
    except OSError:
        return [step_text]

    table = _find_examples_rows(lines, step_line - 1)
    if table is None:
        return [step_text]

    header, data_rows = table
    resolved = [_substitute_row(step_text, header, row) for row in data_rows]
    return resolved or [step_text]
