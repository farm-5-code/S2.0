from concurrent.futures import ThreadPoolExecutor, as_completed
from app.core.logging import get_logger
from app.clients.sofascore_client import get_sofascore_client
from app.services.cache_service import get_cache_service
from app.api.middleware import get_current_request_id
logger=get_logger(__name__)
MIN_QUALITY_FOR_CACHE=0.2
class DataCollector:
    def __init__(self): self.client=get_sofascore_client(); self.cache=get_cache_service()
    def _calculate_data_quality(self, match_data):
        score=0.0; max_score=5.0
        if match_data.get('home_team_stats'): score+=1.0
        if match_data.get('away_team_stats'): score+=1.0
        hr=match_data.get('home_recent',[]); ar=match_data.get('away_recent',[]); h2h=match_data.get('h2h',[])
        score += 1.0 if len(hr)>=3 else (0.5 if len(hr)>=1 else 0)
        score += 1.0 if len(ar)>=3 else (0.5 if len(ar)>=1 else 0)
        score += 1.0 if len(h2h)>=3 else (0.5 if len(h2h)>=1 else 0)
        return round(score/max_score,2)
    def _safe_call(self, label, fn, fallback):
        try: return fn()
        except Exception: return fallback
    def collect(self, home_team_id, away_team_id, sport='football', use_cache=True, force_refresh=False):
        cache_key=[sport,str(home_team_id),str(away_team_id)]
        if use_cache and not force_refresh:
            cached=self.cache.get('matches', cache_key)
            if cached: return cached, True
        data={'home_team_stats':None,'away_team_stats':None,'home_recent':[],'away_recent':[],'h2h':[]}
        futures={}
        with ThreadPoolExecutor(max_workers=5) as ex:
            futures[ex.submit(self._safe_call,'home_team_stats',lambda:self.client.get_team_stats(home_team_id),None)]='home_team_stats'
            futures[ex.submit(self._safe_call,'away_team_stats',lambda:self.client.get_team_stats(away_team_id),None)]='away_team_stats'
            futures[ex.submit(self._safe_call,'home_recent',lambda:self.client.get_team_recent_matches(home_team_id,5),[])]='home_recent'
            futures[ex.submit(self._safe_call,'away_recent',lambda:self.client.get_team_recent_matches(away_team_id,5),[])]='away_recent'
            futures[ex.submit(self._safe_call,'h2h',lambda:self.client.get_h2h_matches(home_team_id,away_team_id),[])]='h2h'
            for f in as_completed(futures):
                try: data[futures[f]]=f.result()
                except Exception: pass
        dq=self._calculate_data_quality(data); data['data_quality']=dq
        if use_cache: self.cache.set('matches', cache_key, data, metadata={'home_team_id':home_team_id,'away_team_id':away_team_id,'data_quality':dq,'degraded': dq<MIN_QUALITY_FOR_CACHE})
        return data, False
_data_collector=None
def get_data_collector():
    global _data_collector
    if _data_collector is None: _data_collector=DataCollector()
    return _data_collector
