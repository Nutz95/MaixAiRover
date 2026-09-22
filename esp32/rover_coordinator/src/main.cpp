/**
 * Rover hardware coordinator — object wiring + FreeRTOS task spawn.
 *
 * MaixCAM2 ↔ ESP UART2 (IO4 RX / IO5 TX). USB UART0 kept for PC console.
 */
#include <Arduino.h>
#include <HardwareSerial.h>

#include "binary_command_handler.h"
#include "board_sensors.h"
#include "command_dispatcher.h"
#include "coordinator_guard.h"
#include "coordinator_lock.h"
#include "drive_failsafe.h"
#include "front_drive_board.h"
#include "protocol_reply.h"
#include "serial_line_reader.h"
#include "settings.h"
#include "wifi_console.h"
#include "wifi_runtime.h"

namespace {

FrontDriveBoard g_motors;
DriveFailsafe g_failsafe;
ProtocolReply g_reply;
WifiRuntime g_wifi;
CoordinatorLock g_lock;
BoardSensors g_sensors;
CommandDispatcher g_commands(g_motors, g_failsafe, g_reply, g_wifi, g_lock, g_sensors);
BinaryCommandHandler g_binary(g_motors, g_failsafe, g_sensors, g_lock);
SerialLineReader g_usbLines;
SerialLineReader g_maixLines;
HardwareSerial g_maixSerial(2);

void commandTask(void * /*arg*/) {
  for (;;) {
    g_reply.setOut(Serial);
    g_usbLines.poll(Serial, g_commands, g_binary, g_reply);

    g_reply.setOut(g_maixSerial);
    g_maixLines.poll(g_maixSerial, g_commands, g_binary, g_reply);

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

  g_maixSerial.setRxBufferSize(256);
  g_maixSerial.begin(
    RoverSettings::kMaixUartBaud,
    SERIAL_8N1,
    RoverSettings::kMaixUartRxPin,
    RoverSettings::kMaixUartTxPin);

  g_lock.begin();
  g_motors.begin();
  g_sensors.begin();

  Serial.println("=== MaixAiRover ESP coordinator (Waveshare front drive) ===");
  Serial.printf(
    "maix-link: UART2 RX=IO%d TX=IO%d @%lu\n",
    RoverSettings::kMaixUartRxPin,
    RoverSettings::kMaixUartTxPin,
    static_cast<unsigned long>(RoverSettings::kMaixUartBaud));
  Serial.println("usb: UART0 CP2102 (PC console)");
  Serial.println("drive: TB6612 FL/FR encoders + PID @ 100Hz");
  Serial.println("text: PING INIT STOP SPEED PWM ENC SCAN WIFI HELP");
  Serial.println("bin:  SYNC=0xA5  PING/STOP/SPEED/PWM/TELEM");
  Serial.flush();

  g_commands.bindWifiThunk();
  WifiConsole::setLineHandler(CommandDispatcher::wifiThunk);

  {
    CoordinatorGuard guard(g_lock);
    g_motors.scan(true);
    g_reply.setOut(Serial);
    if (g_motors.initMotors(0, 0)) {
      g_reply.ok("boot INIT front");
    } else {
      g_reply.err("boot INIT front");
    }
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
  vTaskDelay(pdMS_TO_TICKS(1000));
}
