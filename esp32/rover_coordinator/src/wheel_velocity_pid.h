/**
 * Simple velocity PID in wheel-RPM space (one wheel).
 */
#pragma once

class WheelVelocityPid {
 public:
  /** Reset integrator and last error. */
  void reset();

  /**
   * Compute PWM duty (−max..+max) from target/measured RPM.
   * ``dtSeconds`` must be > 0.
   */
  float update(float targetRpm, float measuredRpm, float dtSeconds);

 private:
  float integral_ = 0.0f;
  float lastError_ = 0.0f;
};
