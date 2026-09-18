/**
 * Rover hardware coordinator — object wiring + FreeRTOS task spawn.
 *
 * MaixCAM2 (UART2 IO14/15) <-> Waveshare ESP32 <-> Hiwonder I2C @ 0x34.
 * Optional WiFi/OTA/console run on a separate core.
 */
#include <Arduino.h>

#include "cam_uart.h"
#include "command_dispatcher.h"
#include "coordinator_lock.h"
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
CoordinatorLock g_lock;
CommandDispatcher g_commands(g_motors, g_failsafe, g_reply, g_wifi, g_lock);
SerialLineReader g_usbLines;
SerialLineReader g_camLines;
CamUart g_camUart;

void commandTask(void * /*arg*/) {
  for (;;) {
    g_usbLines.poll(Serial, g_commands, g_reply);
    g_camLines.poll(g_camUart.stream(), g_commands, g_reply);
    g_failsafe.poll(g_motors, g_reply, g_lock);
    vTaskDelay(pdMS_TO_TICKS(RoverSettings::kCommandTaskPeriodMs));
  }
}

void wifiTask(void * /*arg*/) {
  for (;;) {
    g_wifi.poll();
    vTaskDelay(pdMS_TO_TICKS(RoverSettings::kWifiTaskPeriodMs));
  }
}

}  // namespace

void setup() {
  Serial.begin(RoverSettings::kUsbSerialBaud);
  delay(RoverSettings::kSerialBootDelayMs);

  g_lock.begin();
  g_motors.begin();
  g_camUart.begin();

  Serial.println("=== MaixAiRover ESP coordinator (Waveshare) ===");
  Serial.println("cmds: PING INIT STOP SPEED PWM BAT ENC WIFI SCAN");
  Serial.flush();

  g_commands.bindWifiThunk();
  WifiConsole::setLineHandler(CommandDispatcher::wifiThunk);

  {
    CoordinatorGuard guard(g_lock);
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
  }

  g_wifi.beginBackground();

  xTaskCreatePinnedToCore(
    commandTask,
    "cmd",
    RoverSettings::kCommandTaskStack,
    nullptr,
    RoverSettings::kCommandTaskPriority,
    nullptr,
    RoverSettings::kCommandTaskCore);

  xTaskCreatePinnedToCore(
    wifiTask,
    "wifi",
    RoverSettings::kWifiTaskStack,
    nullptr,
    RoverSettings::kWifiTaskPriority,
    nullptr,
    RoverSettings::kWifiTaskCore);
}

void loop() {
  // Work runs in FreeRTOS tasks; keep Arduino loop idle.
  vTaskDelay(pdMS_TO_TICKS(1000));
}
