import time, random
from typing import Callable, TypeVar, Type, Tuple
from functools import wraps
from app.core.logging import get_logger
logger = get_logger(__name__)
T = TypeVar('T')
class RetryableError(Exception): pass
class NonRetryableError(Exception): pass
RETRYABLE_STATUS_CODES = {408,429,500,502,503,504}
NON_RETRYABLE_STATUS_CODES = {400,401,403,404,405,422}
def classify_http_error(status_code:int):
    return RetryableError if status_code not in NON_RETRYABLE_STATUS_CODES else NonRetryableError

def retry_with_backoff(max_retries=3, backoff_factor=0.5, max_backoff=30.0, jitter=True, retryable_exceptions=(RetryableError, ConnectionError, TimeoutError)):
    def decorator(func:Callable[...,T]):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_retries: raise
                    backoff_time = min(backoff_factor * (2 ** attempt), max_backoff)
                    if jitter:
                        jr = backoff_time * 0.25; backoff_time += random.uniform(-jr, jr)
                    time.sleep(backoff_time)
                except Exception:
                    raise
            raise last_exception
        return wrapper
    return decorator

class RetryStrategy:
    def __init__(self, max_retries=3, backoff_factor=0.5, max_backoff=30.0, jitter=True, retryable_exceptions=(RetryableError, ConnectionError, TimeoutError)):
        self.max_retries=max_retries; self.backoff_factor=backoff_factor; self.max_backoff=max_backoff; self.jitter=jitter; self.retryable_exceptions=retryable_exceptions
    def execute(self, func:Callable[...,T], *args, **kwargs):
        return retry_with_backoff(self.max_retries,self.backoff_factor,self.max_backoff,self.jitter,self.retryable_exceptions)(func)(*args, **kwargs)
