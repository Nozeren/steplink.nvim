"""Extract @given/@when/@then/@step(re("...")) step definitions from a .py file via ast."""
import ast
from dataclasses import dataclass
from pathlib import Path

STEP_DECORATORS = {"given", "when", "then", "step"}


@dataclass
class StepDefinition:
    file: Path
    decorator: str  # given | when | then | step
    pattern: str
    function: str
    decorator_lineno: int
    def_lineno: int


def _decorator_name(call: ast.Call):
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    return None


def _pattern_from_re_call(call: ast.Call):
    """call is the `re(...)` call inside e.g. @given(re(r"..."))."""
    if not call.args:
        return None
    arg = call.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    return None


def extract_step_definitions(path: Path):
    """Return StepDefinition entries for every @given/@when/@then/@step(re(...)) in `path`.

    Malformed or unrecognized decorators are silently skipped rather than raising, so one
    odd file never blocks matching against the rest of the candidate set.
    """
    try:
        source = path.read_text(errors="ignore")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, OSError):
        return []

    results = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            name = _decorator_name(decorator)
            if name not in STEP_DECORATORS:
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Call):
                continue
            inner_call = decorator.args[0]
            if _decorator_name(inner_call) != "re":
                continue
            pattern = _pattern_from_re_call(inner_call)
            if pattern is None:
                continue
            results.append(
                StepDefinition(
                    file=path,
                    decorator=name,
                    pattern=pattern,
                    function=node.name,
                    decorator_lineno=decorator.lineno,
                    def_lineno=node.lineno,
                )
            )
    return results
