"""DepthInferWorker accepts only one frame at a time."""

from __future__ import annotations

import threading
import time

from lib.vision.ball_depth_band import BallDepthBand
from lib.vision.depth_infer_result import DepthInferResult
from lib.vision.depth_infer_worker import DepthInferWorker


def test_depth_infer_worker_rejects_second_frame_while_busy() -> None:
  """While busy, try_submit must not call make_frame (no second alloc)."""
  entered = threading.Event()
  release = threading.Event()

  def run_job(small, observation):
    entered.set()
    release.wait(timeout=2.0)
    return DepthInferResult(
      depth=small,
      band=BallDepthBand.UNKNOWN,
      near_obstacle=False,
      infer_ms=0.0,
    )

  worker = DepthInferWorker(run_job)
  builds: list[str] = []

  def make_first():
    builds.append("a")
    return ("frame-a", None)

  assert worker.try_submit(make_first) is True
  assert entered.wait(timeout=2.0) is True
  assert worker.busy() is True

  def make_second():
    builds.append("b")
    return ("frame-b", None)

  assert worker.try_submit(make_second) is False
  assert builds == ["a"]

  release.set()
  deadline = time.monotonic() + 2.0
  while worker.busy() and time.monotonic() < deadline:
    time.sleep(0.01)
  assert worker.busy() is False
  result = worker.take_result()
  assert result is not None
  assert result.depth == "frame-a"
  worker.stop()
