/**
 * Mutual exclusion for motor + reply paths shared by FreeRTOS tasks.
 */
#pragma once

#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>

class CoordinatorLock {
 public:
  /** Create the mutex (call once from setup). */
  void begin();

  /** Block until the coordinator lock is acquired. */
  void lock();

  /** Release the coordinator lock. */
  void unlock();

 private:
  SemaphoreHandle_t mutex_ = nullptr;
};
