import json
from pathlib import Path
from datetime import datetime, timedelta
from app.core.settings import settings
from app.core.logging import get_logger
from app.api.middleware import get_current_request_id
from app.core.metrics import get_metrics_registry
logger=get_logger(__name__)
class CacheService:
    def __init__(self, base_dir=None):
        self.base_dir=Path(base_dir or settings.CACHE_DIR); self.version=settings.CACHE_VERSION; self.ttl_hours=settings.CACHE_TTL_HOURS; self.metrics=get_metrics_registry(); self.base_dir.mkdir(parents=True, exist_ok=True); self.namespaces=['matches','teams','stats']; [ (self.base_dir/ns).mkdir(exist_ok=True) for ns in self.namespaces ]
    def _build_key(self, namespace, key_parts): return f"{self.version}_{'_'.join(''.join(c if c.isalnum() else '_' for c in str(part)) for part in key_parts)}"
    def _get_cache_path(self, namespace, key): return self.base_dir/namespace/f'{key}.json'
    def _is_expired(self, data):
        try: return datetime.now() - datetime.fromisoformat(data.get('timestamp','2000-01-01')) > timedelta(hours=self.ttl_hours)
        except Exception: return True
    def get(self, namespace, key_parts, allow_stale=False):
        key=self._build_key(namespace,key_parts); path=self._get_cache_path(namespace,key)
        if not path.exists(): self.metrics.inc('cache_misses_total', labels={'namespace':namespace}); return None
        try:
            data=json.loads(path.read_text(encoding='utf-8')); expired=self._is_expired(data)
            if expired and not allow_stale: self.metrics.inc('cache_expired_total', labels={'namespace':namespace}); return None
            self.metrics.inc('cache_hits_total', labels={'namespace':namespace,'stale':str(expired).lower()}); return data.get('data')
        except Exception: return None
    def set(self, namespace, key_parts, data, metadata=None):
        key=self._build_key(namespace,key_parts); path=self._get_cache_path(namespace,key)
        try:
            payload={'version':self.version,'timestamp':datetime.now().isoformat(),'ttl_hours':self.ttl_hours,'metadata':metadata or {},'data':data}; path.write_text(json.dumps(payload,ensure_ascii=False,indent=2), encoding='utf-8'); self.metrics.inc('cache_sets_total', labels={'namespace':namespace}); return True
        except Exception: return False
    def get_stats(self):
        stats={'version':self.version,'ttl_hours':self.ttl_hours,'namespaces':{}}
        for ns in self.namespaces:
            files=list((self.base_dir/ns).glob('*.json')); stats['namespaces'][ns]={'entries':len(files),'size_kb':round(sum(f.stat().st_size for f in files)/1024,2)}
        return stats
_cache_service=None
def get_cache_service():
    global _cache_service
    if _cache_service is None: _cache_service=CacheService()
    return _cache_service
