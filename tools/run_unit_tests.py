"""Stdlib unit-test runner (works when pytest cannot be installed)."""

import importlib.util
import pathlib
import sys
import traceback


def _load_module(path: pathlib.Path):
  spec = importlib.util.spec_from_file_location(path.stem, path)
  module = importlib.util.module_from_spec(spec)
  assert spec.loader is not None
  spec.loader.exec_module(module)
  return module


def main() -> int:
  """Discover and run test_* functions under tests/."""
  root = pathlib.Path(__file__).resolve().parents[1]
  tests_dir = root / "tests"
  app = root / "maixcam" / "roverMecanum"
  sys.path.insert(0, str(app))

  failures = 0
  ran = 0
  for path in sorted(tests_dir.glob("test_*.py")):
    module = _load_module(path)
    for name in sorted(dir(module)):
      if not name.startswith("test_"):
        continue
      func = module.__dict__[name]
      if not callable(func):
        continue
      ran += 1
      try:
        func()
        print(f"OK  {path.name}::{name}")
      except Exception:
        failures += 1
        print(f"FAIL {path.name}::{name}")
        traceback.print_exc()
  print(f"\n{ran - failures} passed, {failures} failed, {ran} total")
  return 1 if failures else 0


if __name__ == "__main__":
  sys.exit(main())
