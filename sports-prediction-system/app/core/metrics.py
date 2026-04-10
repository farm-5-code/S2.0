from threading import Lock
class MetricsRegistry:
    def __init__(self):
        self._lock = Lock(); self._counters = {}; self._gauges = {}
    def _lk(self, labels=None):
        return tuple(sorted((str(k), str(v)) for k, v in (labels or {}).items()))
    def inc(self, name, value=1.0, labels=None):
        key = (name, self._lk(labels))
        with self._lock: self._counters[key] = self._counters.get(key, 0.0) + value
    def set_gauge(self, name, value, labels=None):
        key = (name, self._lk(labels))
        with self._lock: self._gauges[key] = value
    def observe_summary(self, base_name, value, labels=None):
        self.inc(base_name + '_sum', value, labels); self.inc(base_name + '_count', 1.0, labels)
        key = (base_name + '_max', self._lk(labels))
        with self._lock: self._gauges[key] = max(value, self._gauges.get(key, float('-inf')))
    def render_prometheus(self):
        def fl(li):
            return '' if not li else '{' + ','.join(f'{k}="{v}"' for k, v in li) + '}'
        lines=[]
        with self._lock:
            for (n,l),v in sorted(self._counters.items()): lines.append(f'{n}{fl(l)} {v}')
            for (n,l),v in sorted(self._gauges.items()): lines.append(f'{n}{fl(l)} {v}')
        return '\n'.join(lines) + '\n'
_metrics_registry = None
def get_metrics_registry():
    global _metrics_registry
    if _metrics_registry is None: _metrics_registry = MetricsRegistry()
    return _metrics_registry
