from difflib import SequenceMatcher
from app.core.logging import get_logger
from app.core.exceptions import TeamNotFoundError, AppException
from app.storage.repositories.team_repo import get_team_repo
from app.clients.sofascore_client import get_sofascore_client
from app.api.middleware import get_current_request_id
logger=get_logger(__name__)
class TeamResolver:
    def __init__(self): self.team_repo=get_team_repo(); self.sofascore_client=get_sofascore_client(); self._hardcoded_teams=None
    def _load_hardcoded_teams(self):
        if self._hardcoded_teams is None:
            try:
                from config.teams.hardcoded_ids import get_hardcoded_teams
                self._hardcoded_teams=get_hardcoded_teams()
            except ImportError:
                self._hardcoded_teams={}
        return self._hardcoded_teams
    def _calculate_similarity(self,a,b): return SequenceMatcher(None,a.lower(),b.lower()).ratio()
    def _find_best_match(self,query,candidates,threshold=0.8):
        best=None; best_score=0.0
        for c in candidates:
            score=self._calculate_similarity(query,c.get('name',''))
            if c.get('shortName'): score=max(score,self._calculate_similarity(query,c['shortName']))
            if score > best_score: best_score=score; best=c
        return (best,best_score) if best and best_score >= threshold else None
    def resolve(self, team_name, sport, competition=''):
        cached=self.team_repo.get_by_name(team_name,sport,competition)
        if cached: return cached['team_id']
        hardcoded=self._load_hardcoded_teams().get(sport,{})
        comp_key=f'{competition}:{team_name}'
        if comp_key in hardcoded:
            tid=hardcoded[comp_key]; self.team_repo.save(team_name,tid,sport,competition,'hardcoded',1.0); return tid
        if team_name in hardcoded:
            tid=hardcoded[team_name]; self.team_repo.save(team_name,tid,sport,competition,'hardcoded',1.0); return tid
        search_results=[]
        try:
            search_results=self.sofascore_client.search_team(team_name,sport)
            match=self._find_best_match(team_name,search_results)
            if match:
                best,conf=match; tid=best.get('id')
                if tid: self.team_repo.save(team_name,tid,sport,competition,'api_search',conf); return tid
        except Exception: pass
        candidates=[{'name':r.get('name'),'id':r.get('id'),'similarity':round(self._calculate_similarity(team_name,r.get('name','')),2)} for r in search_results[:5]]
        if candidates: raise AppException(f"Team '{team_name}' not found. Found {len(candidates)} similar teams.", 'TEAM_NOT_FOUND_WITH_CANDIDATES', {'team_name':team_name,'sport':sport,'competition':competition,'candidates':candidates})
        raise TeamNotFoundError(team_name,sport,competition)
_team_resolver=None
def get_team_resolver():
    global _team_resolver
    if _team_resolver is None: _team_resolver=TeamResolver()
    return _team_resolver
