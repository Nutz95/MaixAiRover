"""Host guardrail checks for MaixAiRover quality rules."""

import ast
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
LIB = ROOT / "maixcam" / "roverMecanum" / "lib"
MAX_LINES = 400
FORBIDDEN = ("getattr", "setattr")


def _is_public(name: str) -> bool:
  return not name.startswith("_")


def _has_docstring(node) -> bool:
  if not node.body:
    return False
  first = node.body[0]
  if not isinstance(first, ast.Expr):
    return False
  value = first.value
  if isinstance(value, ast.Constant) and isinstance(value.value, str):
    return True
  return False


def check_file(path: pathlib.Path) -> list:
  """Return a list of guardrail violation messages for one file."""
  issues = []
  text = path.read_text(encoding="utf-8")
  lines = text.splitlines()
  if len(lines) > MAX_LINES:
    issues.append(f"{path.name}: {len(lines)} lines > {MAX_LINES}")
  try:
    tree = ast.parse(text, filename=str(path))
  except SyntaxError as exc:
    issues.append(f"{path.name}: syntax error {exc}")
    return issues

  class_defs = [n for n in tree.body if isinstance(n, ast.ClassDef)]
  if len(class_defs) > 1:
    names = ", ".join(c.name for c in class_defs)
    issues.append(f"{path.name}: {len(class_defs)} top-level classes ({names}); need 1 class per file")

  for node in tree.body:
    if isinstance(node, ast.ClassDef) and _is_public(node.name) and not _has_docstring(node):
      issues.append(f"{path.name}: public class {node.name} missing docstring")
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_public(node.name):
      if not _has_docstring(node):
        issues.append(f"{path.name}:{node.lineno}: public function {node.name}() missing docstring")

  for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
      if node.func.id in FORBIDDEN:
        issues.append(f"{path.name}:{node.lineno}: forbidden {node.func.id}()")
    if isinstance(node, ast.ClassDef):
      methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
      if len(methods) > 30:
        issues.append(f"{path.name}: class {node.name} has {len(methods)} methods > 30")
      if _is_public(node.name):
        for method in methods:
          if _is_public(method.name) and not _has_docstring(method):
            issues.append(
              f"{path.name}:{method.lineno}: public method {node.name}.{method.name}() missing docstring"
            )
  return issues


def main() -> int:
  """Scan lib/ and exit non-zero when quality guardrails fail."""
  all_issues = []
  files = sorted(LIB.glob("*.py"))
  for path in files:
    all_issues.extend(check_file(path))
  if all_issues:
    print("GUARDRAIL FAILURES:")
    for issue in all_issues:
      print(f"  - {issue}")
    return 1
  print(f"OK: scanned {len(files)} lib files")
  return 0


if __name__ == "__main__":
  sys.exit(main())
