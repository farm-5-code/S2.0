import time
from enum import Enum
from functools import wraps
from app.core.logging import get_logger
from app.core.exceptions import CircuitBreakerOpenError
logger = get_logger(__name__)
class CircuitState(Enum): CLOSED='closed'; OPEN='open'; HALF_OPEN='half_open'
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60, success_threshold=2, name=None):
        self.failure_threshold=failure_threshold; self.recovery_timeout=recovery_timeout; self.success_threshold=success_threshold; self.name=name or 'unknown'; self.failure_count=0; self.success_count=0; self.last_failure_time=None; self.state=CircuitState.CLOSED
    def _should_attempt_reset(self):
        return self.last_failure_time is not None and (time.time()-self.last_failure_time)>=self.recovery_timeout
    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED; self.failure_count = 0; self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    def _on_failure(self, exception):
        self.failure_count += 1; self.last_failure_time = time.time(); self.success_count = 0
        if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold: self.state = CircuitState.OPEN
    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset(): self.state = CircuitState.HALF_OPEN
            else: raise CircuitBreakerOpenError(self.name)
        try:
            result = func(*args, **kwargs); self._on_success(); return result
        except Exception as e:
            self._on_failure(e); raise
    def protect(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs): return self.call(func, *args, **kwargs)
        return wrapper
    def get_state(self): return self.state.value
    def get_stats(self): return {'name':self.name,'state':self.state.value,'failure_count':self.failure_count,'success_count':self.success_count,'failure_threshold':self.failure_threshold,'recovery_timeout':self.recovery_timeout}
