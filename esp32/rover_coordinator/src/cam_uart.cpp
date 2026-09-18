#include "cam_uart.h"

#include <Arduino.h>

void CamUart::begin() {
  serial_.begin(
    RoverSettings::kCamUartBaud,
    SERIAL_8N1,
    RoverSettings::kCamUartRxPin,
    RoverSettings::kCamUartTxPin);
  Serial.printf(
    "cam-uart: UART%d RX=GPIO%d TX=GPIO%d @ %lu\n",
    RoverSettings::kCamUartNum,
    RoverSettings::kCamUartRxPin,
    RoverSettings::kCamUartTxPin,
    static_cast<unsigned long>(RoverSettings::kCamUartBaud));
}

HardwareSerial &CamUart::stream() {
  return serial_;
}
