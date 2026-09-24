"""Hiwonder 4-channel encoder motor driver register map."""

from enum import IntEnum


class HiwonderRegisters(IntEnum):
  """Register addresses and motor-type constants for the Hiwonder board."""

  ADC_BAT = 0x00
  MOTOR_TYPE = 0x14
  ENCODER_POLARITY = 0x15
  FIXED_PWM = 0x1F
  FIXED_SPEED = 0x33
  ENCODER_TOTAL = 0x3C

  MOTOR_TYPE_WITHOUT_ENCODER = 0
  MOTOR_TYPE_TT = 1
  MOTOR_TYPE_N20 = 2
  MOTOR_TYPE_JGB = 3

  DEFAULT_ADDRESS = 0x34
