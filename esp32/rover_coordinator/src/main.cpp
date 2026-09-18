/**
 * Rover hardware coordinator — object wiring only.
 *
 * MaixCAM2 (UART) <-> Waveshare ESP32 <-> Hiwonder I2C @ 0x34.
 * Optional WiFi: ArduinoOTA + TCP console (same line protocol).
 */
#include <Arduino.h>

#include "command_dispatcher.h"
#include "drive_failsafe.h"
#include "hiwonder_motor_board.h"
#include "protocol_reply.h"
#include "serial_line_reader.h"
#include "settings.h"
#include "wifi_console.h"
#include "wifi_runtime.h"

namespace {

HiwonderMotorBoard g_motors;
DriveFailsafe g_failsafe;
ProtocolReply g_reply;
WifiRuntime g_wifi;
CommandDispatcher g_commands(g_motors, g_failsafe, g_reply, g_wifi);
SerialLineReader g_serial;

}  // namespace

void setup() {
  Serial.begin(RoverSettings::kSerialBaud);
  delay(RoverSettings::kSerialBootDelayMs);

  g_motors.begin();

  Serial.println("=== MaixAiRover ESP coordinator (Waveshare) ===");
  Serial.println("cmds: PING INIT STOP SPEED PWM BAT ENC WIFI SCAN");
  Serial.flush();

  g_commands.bindWifiThunk();
  WifiConsole::setLineHandler(CommandDispatcher::wifiThunk);

  g_motors.scan(true);

  if (g_motors.initMotors(
        RoverSettings::kDefaultMotorTypeJgb,
        RoverSettings::kDefaultEncoderPolarity)) {
    g_reply.ok("boot INIT");
  } else {
    g_reply.err("boot INIT - check Hiwonder I2C (VM+GND+SDA=GPIO32/SCL=GPIO33)");
  }
  g_motors.stop();
  g_failsafe.clear();
  g_wifi.beginBackground();
}

void loop() {
  g_serial.poll(g_commands, g_reply);
  g_wifi.poll();
  g_failsafe.poll(g_motors, g_reply);
}
