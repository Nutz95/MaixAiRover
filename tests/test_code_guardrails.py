"""Fail CI when lib/ violates MaixAiRover quality guardrails."""

from __future__ import annotations

import ast
import json
import os
import sys

LIB_DIR = os.path.join(
  os.path.dirname(__file__), "..", "maixcam", "roverMecanum", "lib",
)
CONFIG_JSON = os.path.join(
  os.path.dirname(__file__), "..", "maixcam", "roverMecanum", "config.json",
)


def _iter_lib_py() -> list[str]:
  root = os.path.abspath(LIB_DIR)
  paths = []
  for name in os.listdir(root):
    if name.endswith(".py") and name != "__init__.py":
      paths.append(os.path.join(root, name))
  return sorted(paths)


def test_one_top_level_class_per_file() -> None:
  """Each lib module may define at most one top-level class (incl. Protocol/Enum)."""
  violations = []
  for path in _iter_lib_py():
    with open(path, encoding="utf-8") as handle:
      tree = ast.parse(handle.read(), filename=path)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    if len(classes) > 1:
      names = ", ".join(c.name for c in classes)
      violations.append(f"{os.path.basename(path)}: {len(classes)} classes ({names})")
  assert not violations, "1 class = 1 file:\n  " + "\n  ".join(violations)


def test_no_tuple_return_annotations() -> None:
  """Public callables must not annotate returns as tuple[...] (use a dataclass)."""
  violations = []
  for path in _iter_lib_py():
    with open(path, encoding="utf-8") as handle:
      tree = ast.parse(handle.read(), filename=path)
    for node in ast.walk(tree):
      if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        continue
      if node.name.startswith("_"):
        continue
      if node.returns is None:
        continue
      text = ast.unparse(node.returns)
      if text.startswith("tuple[") or text.startswith("Tuple["):
        violations.append(f"{os.path.basename(path)}:{node.lineno} {node.name} -> {text}")
  assert not violations, "no tuple returns:\n  " + "\n  ".join(violations)


def test_no_dict_list_return_annotations() -> None:
  """Public callables must not return bare dict/list (use a dataclass)."""
  # I2C bus scan() and checklist log_lines() are ordered primitive collections, not DTOs.
  allow = {
    ("i2c_bus.py", "scan"),
    ("maix_i2c_bus.py", "scan"),
    ("stub_i2c_bus.py", "scan"),
    ("stub_i2c_bus.py", "transactions"),
    ("peripheral_checklist.py", "log_lines"),
  }
  violations = []
  for path in _iter_lib_py():
    base = os.path.basename(path)
    with open(path, encoding="utf-8") as handle:
      tree = ast.parse(handle.read(), filename=path)
    for node in ast.walk(tree):
      if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        continue
      if node.name.startswith("_"):
        continue
      if (base, node.name) in allow:
        continue
      if node.returns is None:
        continue
      text = ast.unparse(node.returns)
      if text in ("dict", "list") or text.startswith("dict[") or text.startswith("list["):
        violations.append(f"{base}:{node.lineno} {node.name} -> {text}")
  assert not violations, "no dict/list returns:\n  " + "\n  ".join(violations)


def test_no_getattr_setattr() -> None:
  """Forbid getattr/setattr in lib (explicit attributes only)."""
  violations = []
  for path in _iter_lib_py():
    with open(path, encoding="utf-8") as handle:
      tree = ast.parse(handle.read(), filename=path)
    for node in ast.walk(tree):
      if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in ("getattr", "setattr"):
          violations.append(f"{os.path.basename(path)}:{node.lineno} {node.func.id}()")
  assert not violations, "no getattr/setattr:\n  " + "\n  ".join(violations)


def test_shipped_drive_backend_valid() -> None:
  """config.json drive_backend must be a known DriveBackendKind value."""
  with open(CONFIG_JSON, encoding="utf-8") as handle:
    root = json.load(handle)
  raw = str(root.get("drive_backend", "")).strip().lower()
  assert raw in ("esp", "yahboom"), f"drive_backend={raw!r} invalid"


def main() -> None:
  test_one_top_level_class_per_file()
  test_no_tuple_return_annotations()
  test_no_dict_list_return_annotations()
  test_no_getattr_setattr()
  test_shipped_drive_backend_valid()
  print("code_guardrails: ok")


if __name__ == "__main__":
  main()
  sys.exit(0)
