"""Background DepthAnything runner — at most one frame in flight."""

from __future__ import annotations

import threading
from time import monotonic
from typing import Callable, Optional

from lib.ball_follow.ball_observation import BallObservation
from lib.vision.depth_infer_result import DepthInferResult


class DepthInferWorker:
  """Single in-flight depth job: no queue, no second image while busy."""

  def __init__(self, run_job: Callable) -> None:
    """``run_job(small_img, observation) -> DepthInferResult | None``."""
    self._run_job = run_job
    self._lock = threading.Lock()
    self._wake = threading.Event()
    self._stop = threading.Event()
    self._busy = False
    self._pending_img = None
    self._pending_obs: Optional[BallObservation] = None
    self._result: Optional[DepthInferResult] = None
    self._thread = threading.Thread(
      target=self._loop, daemon=True, name="depth-infer",
    )
    self._thread.start()

  def busy(self) -> bool:
    """True from slot acquire until the NN pass finishes."""
    with self._lock:
      return self._busy

  def try_submit(self, make_frame: Callable) -> bool:
    """Reserve the only slot, then build the frame.

    ``make_frame()`` must return ``(small_img, observation)`` or ``None``.
    Returns False if inference is still running — ``make_frame`` is not called,
    so no extra RGB copy is allocated.
    """
    with self._lock:
      if self._busy:
        return False
      # Hold the slot before any copy/resize so HUD never piles frames.
      self._busy = True
    try:
      built = make_frame()
    except Exception as build_error:
      print(f"depth: frame build: {build_error}")
      with self._lock:
        self._busy = False
      return False
    if built is None:
      with self._lock:
        self._busy = False
      return False
    small_img, observation = built
    if small_img is None:
      with self._lock:
        self._busy = False
      return False
    with self._lock:
      # Still the only pending buffer — never overwrite an in-flight job.
      self._pending_img = small_img
      self._pending_obs = observation
    self._wake.set()
    return True

  def take_result(self) -> Optional[DepthInferResult]:
    """Pop the latest finished result, if any."""
    with self._lock:
      result = self._result
      self._result = None
      return result

  def stop(self) -> None:
    """Wake the worker so it can exit (daemon; best-effort)."""
    self._stop.set()
    self._wake.set()

  def _loop(self) -> None:
    while not self._stop.is_set():
      self._wake.wait(timeout=0.5)
      self._wake.clear()
      if self._stop.is_set():
        break
      with self._lock:
        small = self._pending_img
        obs = self._pending_obs
        self._pending_img = None
        self._pending_obs = None
      if small is None:
        with self._lock:
          self._busy = False
        continue
      try:
        t0 = monotonic()
        result = self._run_job(small, obs)
        # Drop the input buffer reference ASAP — only depth result may remain.
        small = None
        if result is not None:
          result.infer_ms = (monotonic() - t0) * 1000.0
          with self._lock:
            self._result = result
      except Exception as job_error:
        print(f"depth: worker: {job_error}")
      finally:
        # Only now may the HUD submit the next fresh frame.
        with self._lock:
          self._busy = False
