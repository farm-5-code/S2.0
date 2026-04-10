import time
from threading import Lock
class InMemoryRateLimiter:
    def __init__(self, requests_per_minute=60):
        self.requests_per_minute=requests_per_minute; self.window_seconds=60; self._lock=Lock(); self._buckets={}
    def check(self, key:str):
        now=int(time.time()); window_start = now - (now % self.window_seconds)
        with self._lock:
            stored=self._buckets.get(key)
            if stored is None or stored[0] != window_start:
                self._buckets[key]=(window_start,1)
                return True, self.requests_per_minute-1, self.window_seconds-(now-window_start)
            count=stored[1]
            if count >= self.requests_per_minute:
                return False, 0, self.window_seconds-(now-window_start)
            count += 1; self._buckets[key]=(window_start,count)
            return True, self.requests_per_minute-count, self.window_seconds-(now-window_start)
