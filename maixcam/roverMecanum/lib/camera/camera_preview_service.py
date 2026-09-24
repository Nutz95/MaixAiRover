"""Camera capture thread paced for MaixCAM multi-core + GIL friendliness."""

import gc
import threading

from maix import app, camera, image, time

_FORMATS = {
  "rgb888": image.Format.FMT_RGB888,
  "bgr888": image.Format.FMT_BGR888,
  "yuv420": image.Format.FMT_YVU420SP,
  "nv21": image.Format.FMT_YVU420SP,
  "yuv420sp": image.Format.FMT_YVU420SP,
}

_STOP_JOIN_S = 2.5


def _resolve_format(name):
  """
  Resolve camera pixel format.

  HUD uses ``draw_*`` which MaixCAM2 only supports on RGB/BGR. YUV capture
  cannot be converted with ``to_format`` either (Not implemented), so map
  any YUV request to RGB888 and log once.
  """
  key = (name or "rgb888").strip().lower()
  if key in ("yuv420", "nv21", "yuv420sp", "yvu420sp"):
    print(f"camera: {key} cannot HUD-draw on MaixCAM2 → rgb888")
    key = "rgb888"
  if key in _FORMATS:
    return _FORMATS[key]
  return image.Format.FMT_RGB888


class CameraPreviewService:
  """Camera capture on a worker thread; display thread only samples latest frame."""

  def __init__(self, disp, capture_w=0, capture_h=0, fps=20, pixel_format="rgb888"):
    self._disp = disp
    # 0 = match display (avoids a second resize channel + keeps FPS up).
    self._capture_w = int(capture_w) if int(capture_w) > 0 else int(disp.width())
    self._capture_h = int(capture_h) if int(capture_h) > 0 else int(disp.height())
    self._fps = max(1, min(60, int(fps)))
    self._pixel_format = pixel_format
    self._lock = threading.Lock()
    self._hw_lock = threading.Lock()
    self._latest = None
    self._cam = None
    self._preview = None
    self._direct_read = False
    self._thread = None
    self._stop = threading.Event()
    self._paused = threading.Event()
    self._ready = threading.Event()
    self._error = ""
    self._released = False

  @property
  def error(self):
    """Return the last camera open/runtime error, or empty string."""
    return self._error

  @property
  def ready(self):
    """Return True once the preview thread has opened the camera."""
    return self._ready.is_set()

  def start(self):
    """Start the preview worker and wait briefly for the first ready state."""
    if self._thread and self._thread.is_alive():
      return
    self._stop.clear()
    self._paused.clear()
    self._ready.clear()
    self._released = False
    self._thread = threading.Thread(target=self._worker, daemon=True, name="cam-preview")
    self._thread.start()
    deadline = time.ticks_ms() + 8000
    while not self._ready.is_set() and time.ticks_ms() < deadline:
      if self._error:
        break
      self._ready.wait(timeout=0.02)

  def stop(self):
    """Signal the worker to stop; release HW only after the worker exits."""
    self._stop.set()
    self._paused.clear()
    thread = self._thread
    if thread is not None and thread.is_alive():
      thread.join(timeout=_STOP_JOIN_S)
      if thread.is_alive():
        print("camera: stop join timed out — worker still owns hardware")
        return
    # Worker already ran finally → _release_hw; only clean up if it never started.
    self._release_hw()
    self._thread = None

  def set_paused(self, paused: bool) -> None:
    """Pause capture (frees CPU while checklist / UART probe runs)."""
    if paused:
      self._paused.set()
    else:
      self._paused.clear()

  def get_frame(self):
    """Return the latest preview frame, or None if none is ready."""
    with self._lock:
      return self._latest

  def _open_camera(self):
    fmt = _resolve_format(self._pixel_format)
    label = "rgb888" if fmt == image.Format.FMT_RGB888 else (
      "bgr888" if fmt == image.Format.FMT_BGR888 else self._pixel_format
    )
    cam = camera.Camera(self._capture_w, self._capture_h, fmt, fps=self._fps)
    print(f"camera: {self._capture_w}x{self._capture_h} {label} @{self._fps}fps")
    return cam

  def _worker(self):
    try:
      self._direct_read = (
        self._capture_w == self._disp.width() and self._capture_h == self._disp.height()
      )
      self._cam = self._open_camera()
      if not self._direct_read:
        self._preview = self._cam.add_channel(self._disp.width(), self._disp.height())
        print(f"camera: preview channel {self._disp.width()}x{self._disp.height()}")
      else:
        print("camera: direct read (display-sized, no resize)")

      self._ready.set()
      while not self._stop.is_set() and not app.need_exit():
        if self._paused.is_set():
          self._stop.wait(timeout=0.04)
          continue
        frame = None
        try:
          if self._direct_read:
            frame = self._cam.read()
          else:
            frame = self._preview.read()
        except Exception as camera_error:
          self._error = str(camera_error)
          print(f"camera read: {camera_error}")
        if frame is not None:
          with self._lock:
            self._latest = frame
          self._stop.wait(timeout=0.001)
        else:
          self._stop.wait(timeout=0.005)
    except Exception as exc:
      self._error = str(exc)
      print(f"camera error: {exc}")
    finally:
      self._release_hw()

  def _release_hw(self):
    """Idempotent camera teardown (only one caller deletes native handles)."""
    with self._hw_lock:
      if self._released:
        return
      self._released = True
    self._ready.clear()
    with self._lock:
      self._latest = None
    try:
      if self._preview is not None:
        del self._preview
    except Exception as release_error:
      print(f"camera: preview release failed: {release_error}")
    self._preview = None
    try:
      if self._cam is not None:
        del self._cam
    except Exception as release_error:
      print(f"camera: camera release failed: {release_error}")
    self._cam = None
    gc.collect()
    print("camera: released")
