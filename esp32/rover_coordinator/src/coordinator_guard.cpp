#include "coordinator_guard.h"

CoordinatorGuard::CoordinatorGuard(CoordinatorLock &lock) : lock_(lock) {
  lock_.lock();
}

CoordinatorGuard::~CoordinatorGuard() {
  lock_.unlock();
}
