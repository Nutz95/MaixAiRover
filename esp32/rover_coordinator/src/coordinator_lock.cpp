#include "coordinator_lock.h"

void CoordinatorLock::begin() {
  if (mutex_ == nullptr) {
    mutex_ = xSemaphoreCreateRecursiveMutex();
  }
}

void CoordinatorLock::lock() {
  if (mutex_ != nullptr) {
    xSemaphoreTakeRecursive(mutex_, portMAX_DELAY);
  }
}

void CoordinatorLock::unlock() {
  if (mutex_ != nullptr) {
    xSemaphoreGiveRecursive(mutex_);
  }
}
