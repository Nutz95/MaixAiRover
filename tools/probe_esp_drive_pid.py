"""
Auto encoder / PID balance probe on MaixCAM2 (no manual watching).

Runs open-loop PWM then closed-loop SPEED, samples TELEM encoder deltas,
prints FL vs FR rates and a recommended enc-invert hint.

  python3 /tmp/probe_esp_drive_pid.py --port uart4
"""

from __future__ import annotations

import argparse
import os
import sys
import time

# Allow running from /tmp with deployed lib on device, or repo layout on host.
for path in ("/root/roverMecanum", os.path.join(os.path.dirname(__file__), "..", "maixcam", "roverMecanum")):
  if os.path.isdir(path) and path not in sys.path:
    sys.path.insert(0, path)

from lib.esp_binary_client import EspBinaryClient  # noqa: E402


def _sample_rates(client: EspBinaryClient, seconds: float) -> tuple[float, float, int, int]:
  """Return (rpm_fl_est, rpm_fr_est, d_fl, d_fr) over ``seconds`` using TELEM enc."""
  t0 = client.telem(timeout_s=0.5)
  time.sleep(seconds)
  t1 = client.telem(timeout_s=0.5)
  dt = max(0.001, seconds)
  d_fl = t1.enc_fl - t0.enc_fl
  d_fr = t1.enc_fr - t0.enc_fr
  # Same model as firmware: 2464 counts/rev → RPM = delta/2464 * 60/dt
  cpr = 2464.0
  rpm_fl = (d_fl / cpr) * (60.0 / dt)
  rpm_fr = (d_fr / cpr) * (60.0 / dt)
  return rpm_fl, rpm_fr, d_fl, d_fr


def _run_phase(client: EspBinaryClient, label: str, kind: str, left: int, right: int, seconds: float) -> None:
  print(f"\n==> {label}: {kind} {left} {right} for {seconds:.1f}s")
  if kind == "pwm":
    client.pwm(left, right, 0, 0, timeout_s=0.3)
  else:
    client.speed(left, right, 0, 0, timeout_s=0.3)
  rpm_fl, rpm_fr, d_fl, d_fr = _sample_rates(client, seconds)
  client.stop(timeout_s=0.3)
  time.sleep(0.35)
  ratio = (rpm_fl / rpm_fr) if abs(rpm_fr) > 1.0 else float("inf")
  print(f"  delta enc FL/FR = {d_fl} / {d_fr}")
  print(f"  RPM est   FL/FR = {rpm_fl:.1f} / {rpm_fr:.1f}  (FL/FR={ratio:.3f})")
  if abs(rpm_fl) < 2 and abs(rpm_fr) < 2:
    print("  WARN: almost no encoder motion — check wiring / invert / power")
  elif abs(rpm_fl) < 2:
    print("  WARN: FL encoder quiet (left) while FR moves")
  elif abs(rpm_fr) < 2:
    print("  WARN: FR encoder quiet (right) while FL moves")
  elif rpm_fl * rpm_fr < 0:
    print("  WARN: opposite encoder signs — flip kInvertEncA or kInvertEncB")
  elif abs(ratio - 1.0) > 0.15:
    print("  WARN: >15% speed mismatch under equal command")


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument("--port", default="uart4", choices=("uart2", "uart4"))
  parser.add_argument("--pwm", type=int, default=40, help="open-loop PWM magnitude")
  parser.add_argument("--speed", type=int, default=20, help="closed-loop SPEED magnitude")
  parser.add_argument("--seconds", type=float, default=1.2)
  args = parser.parse_args()

  client = EspBinaryClient(uart_port=args.port)
  print(f"open binary link port={args.port}")
  client.open()
  print(f"link={client.link_name} PING ok")
  try:
    client.text_command("INIT")
  except Exception as exc:
    print(f"INIT: {exc}")

  mag_p = abs(int(args.pwm))
  mag_s = abs(int(args.speed))
  hold = max(0.6, float(args.seconds))

  # Open-loop: both should spin similarly if motors+encoders healthy.
  _run_phase(client, "PWM both", "pwm", mag_p, mag_p, hold)
  _run_phase(client, "PWM left-only", "pwm", mag_p, 0, hold)
  _run_phase(client, "PWM right-only", "pwm", 0, mag_p, hold)

  # Closed-loop: mismatch here = PID/encoder scale/sign issue.
  _run_phase(client, "SPEED both", "speed", mag_s, mag_s, hold)
  _run_phase(client, "SPEED left-only", "speed", mag_s, 0, hold)
  _run_phase(client, "SPEED right-only", "speed", 0, mag_s, hold)

  client.stop(timeout_s=0.3)
  client.close()
  print("\nDone. If SPEED both mismatches but PWM both matches → encoder/PID.")
  print("If PWM both already mismatches → mechanical / motor wiring.")
  return 0


if __name__ == "__main__":
  try:
    raise SystemExit(main())
  except Exception as exc:
    print(f"FAIL: {exc}")
    raise SystemExit(1)
