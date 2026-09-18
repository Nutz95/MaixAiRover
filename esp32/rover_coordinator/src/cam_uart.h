/**
 * MaixCAM UART2 on Waveshare Dupont IO14/IO15.
 */
#pragma once

#include <HardwareSerial.h>

#include "settings.h"

class CamUart {
 public:
  /** Begin UART2 on the configured RX/TX pins. */
  void begin();

  /** Underlying stream for the line reader. */
  HardwareSerial &stream();

 private:
  HardwareSerial serial_{RoverSettings::kCamUartNum};
};
