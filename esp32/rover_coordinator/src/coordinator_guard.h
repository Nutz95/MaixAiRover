/**
 * RAII guard around CoordinatorLock.
 */
#pragma once

#include "coordinator_lock.h"

class CoordinatorGuard {
 public:
  /** Acquire ``lock`` for the lifetime of this guard. */
  explicit CoordinatorGuard(CoordinatorLock &lock);

  /** Release the lock. */
  ~CoordinatorGuard();

  CoordinatorGuard(const CoordinatorGuard &) = delete;
  CoordinatorGuard &operator=(const CoordinatorGuard &) = delete;

 private:
  CoordinatorLock &lock_;
};
