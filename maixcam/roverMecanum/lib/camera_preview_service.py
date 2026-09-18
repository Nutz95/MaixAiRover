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


def _resolve_format(name):
  key = (name or "yuv420").strip().lower()
  if key in _FORMATS:
    return _FORMATS[key]
  return image.Format.FMT_YVU420SP


class CameraPreviewService:
  """Camera capture thread — paced to avoid starving MaixPy GIL / input poll."""

  def __init__(self, disp, capture_w=1280, capture_h=720, fps=30, pixel_format="yuv420"):
    self._disp = disp
    self._capture_w = int(capture_w)
    self._capture_h = int(capture_h)
    self._fps = max(1, min(60, int(fps)))
    self._pace_ms = max(1, int(1000 / self._fps))
    self._pixel_format = pixel_format
    self._lock = threading.Lock()
    self._latest = None
    self._cam = None
    self._preview = None
    self._direct_read = False
    self._thread = None
    self._stop = threading.Event()
    self._ready = threading.Event()
    self._error = ""

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
    self._ready.clear()
    self._thread = threading.Thread(target=self._worker, daemon=True)
    self._thread.start()
    deadline = time.ticks_ms() + 8000
    while not self._ready.is_set() and time.ticks_ms() < deadline:
      if self._error:
        break
      time.sleep_ms(20)

  def stop(self):
    """Stop the preview worker and release camera hardware."""
    if self._stop.is_set() and self._cam is None:
      return
    self._stop.set()
    if self._thread and self._thread.is_alive():
      self._thread.join(timeout=2.5)
    self._release_hw()
    self._thread = None

  def get_frame(self):
    """Return the latest preview frame, or None if none is ready."""
    with self._lock:
      return self._latest

  def _open_camera(self):
    fmt = _resolve_format(self._pixel_format)
    label = self._pixel_format
    try:
      cam = camera.Camera(self._capture_w, self._capture_h, fmt, fps=self._fps)
      print(f"camera: {self._capture_w}x{self._capture_h} {label} @{self._fps}fps")
      return cam
    except Exception as exc:
      if fmt == image.Format.FMT_YVU420SP:
        raise
      print(f"camera: {label} failed ({exc}), fallback yuv420")
      cam = camera.Camera(
        self._capture_w, self._capture_h, image.Format.FMT_YVU420SP, fps=self._fps,
      )
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
        print("camera: direct read (no resize channel)")

      self._ready.set()
      while not self._stop.is_set() and not app.need_exit():
        frame = None
        try:
          if self._direct_read:
            frame = self._cam.read()
          else:
            frame = self._preview.read()
        except Exception:
          pass
        if frame is not None:
          with self._lock:
            self._latest = frame
        time.sleep_ms(self._pace_ms)
    except Exception as exc:
      self._error = str(exc)
      print(f"camera error: {exc}")
    finally:
      self._release_hw()

  def _release_hw(self):
    self._ready.clear()
    with self._lock:
      self._latest = None
    try:
      if self._preview is not None:
        del self._preview
    except Exception:
      pass
    self._preview = None
    try:
      if self._cam is not None:
        del self._cam
    except Exception:
      pass
    self._cam = None
    gc.collect()
    print("camera: released")
