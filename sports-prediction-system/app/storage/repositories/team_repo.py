import json
from app.storage.database import get_team_cache_db
class TeamRepository:
    def __init__(self): self.db=get_team_cache_db()
    def get_by_name(self, team_name, sport, competition=''):
        q="SELECT * FROM team_cache WHERE team_name = ? AND sport = ? AND competition = ? ORDER BY last_verified DESC LIMIT 1"
        result=self.db.fetchone(q,(team_name,sport,competition))
        if result or not competition: return result
        q2="SELECT * FROM team_cache WHERE team_name = ? AND sport = ? AND competition = '' ORDER BY last_verified DESC LIMIT 1"
        return self.db.fetchone(q2,(team_name,sport))
    def save(self, team_name, team_id, sport, competition='', source='manual', confidence=1.0, aliases=None):
        existing=self.get_by_name(team_name,sport,competition)
        if existing:
            q="UPDATE team_cache SET team_id=?, source=?, confidence=?, aliases=?, last_verified=CURRENT_TIMESTAMP WHERE id=?"
            self.db.execute(q,(team_id,source,confidence,json.dumps(aliases) if aliases else None,existing['id']))
            return existing['id']
        q="INSERT INTO team_cache (team_name,team_id,sport,competition,source,confidence,aliases,last_verified) VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP)"
        return self.db.execute(q,(team_name,team_id,sport,competition,source,confidence,json.dumps(aliases) if aliases else None))
    def get_all_for_sport(self, sport, competition=''):
        if competition: return self.db.fetchall('SELECT * FROM team_cache WHERE sport = ? AND competition = ? ORDER BY team_name',(sport,competition))
        return self.db.fetchall('SELECT * FROM team_cache WHERE sport = ? ORDER BY team_name',(sport,))
_team_repo=None
def get_team_repo():
    global _team_repo
    if _team_repo is None: _team_repo=TeamRepository()
    return _team_repo
