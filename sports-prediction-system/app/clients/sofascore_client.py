from datetime import datetime
from app.clients.base_client import BaseHTTPClient
from app.core.settings import settings
from app.resilience.timeout import TimeoutConfig
class SofaScoreClient(BaseHTTPClient):
    def __init__(self):
        super().__init__(settings.SOFASCORE_BASE_URL,'sofascore',TimeoutConfig(2.0, float(settings.API_TIMEOUT)),True)
    def get_team_stats(self, team_id):
        try: return self.get(f'/team/{team_id}/statistics')
        except Exception: return None
    def get_team_recent_matches(self, team_id, limit=5):
        try: return self.get(f'/team/{team_id}/events/last/{limit}').get('events',[])
        except Exception: return []
    def get_h2h_matches(self, team1_id, team2_id):
        try: return self.get(f'/teams/h2h/{team1_id}/{team2_id}').get('events',[])
        except Exception: return []
    def search_team(self, query, sport='football'):
        try: return self.get('/search', params={'q':query,'type':'team','sport':sport}).get('results',{}).get('teams',[])
        except Exception: return []
    def get_scheduled_events_for_date(self, sport, date_str):
        try: return self.get(f'/sport/{sport}/scheduled-events/{date_str}').get('events',[])
        except Exception: return []
    def find_scheduled_match(self, sport, home_team_id, away_team_id, date_str=None):
        date_str = date_str or datetime.utcnow().strftime('%Y-%m-%d')
        for event in self.get_scheduled_events_for_date(sport, date_str):
            if event.get('homeTeam',{}).get('id') == home_team_id and event.get('awayTeam',{}).get('id') == away_team_id: return event
        return None
_sofascore_client=None
def get_sofascore_client():
    global _sofascore_client
    if _sofascore_client is None: _sofascore_client=SofaScoreClient()
    return _sofascore_client
