import json
from app.storage.database import get_analysis_db
class AnalysisRepository:
    def __init__(self): self.db=get_analysis_db()
    def _parse_json_fields(self,result):
        if result.get('engine_factors'): result['factors']=json.loads(result['engine_factors']); del result['engine_factors']
        if result.get('features_json'): result['features']=json.loads(result['features_json']); del result['features_json']
        return result
    def save(self, sport, competition, home_team, away_team, home_team_id, away_team_id, prediction_outcome, home_win_probability, draw_probability, away_win_probability, confidence_score, engine_version, engine_factors, features, data_quality_score, cached, request_id=None, event_id=None, scheduled_start_time=None, analysis_source='api'):
        q="""INSERT INTO analyses (sport,competition,home_team,away_team,home_team_id,away_team_id,event_id,scheduled_start_time,prediction_outcome,home_win_probability,draw_probability,away_win_probability,confidence_score,engine_version,engine_factors,features_json,data_quality_score,cached,request_id,analysis_source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
        return self.db.execute(q,(sport,competition,home_team,away_team,home_team_id,away_team_id,event_id,scheduled_start_time,prediction_outcome,home_win_probability,draw_probability,away_win_probability,confidence_score,engine_version,json.dumps(engine_factors),json.dumps(features),data_quality_score,cached,request_id,analysis_source))
    def get_recent(self, limit=10): return [self._parse_json_fields(dict(r)) for r in self.db.fetchall('SELECT * FROM analyses ORDER BY created_at DESC LIMIT ?',(limit,))]
    def search_by_teams(self, home_team=None, away_team=None, limit=50):
        if home_team and away_team: rows=self.db.fetchall('SELECT * FROM analyses WHERE home_team LIKE ? AND away_team LIKE ? ORDER BY created_at DESC LIMIT ?',(f'%{home_team}%',f'%{away_team}%',limit))
        elif home_team: rows=self.db.fetchall('SELECT * FROM analyses WHERE home_team LIKE ? OR away_team LIKE ? ORDER BY created_at DESC LIMIT ?',(f'%{home_team}%',f'%{home_team}%',limit))
        elif away_team: rows=self.db.fetchall('SELECT * FROM analyses WHERE home_team LIKE ? OR away_team LIKE ? ORDER BY created_at DESC LIMIT ?',(f'%{away_team}%',f'%{away_team}%',limit))
        else: rows=self.db.fetchall('SELECT * FROM analyses ORDER BY created_at DESC LIMIT ?',(limit,))
        return [self._parse_json_fields(dict(r)) for r in rows]
    def update_actual_result(self, analysis_id, actual_outcome, actual_home_score, actual_away_score):
        self.db.execute('UPDATE analyses SET actual_outcome=?, actual_home_score=?, actual_away_score=? WHERE id=?',(actual_outcome,actual_home_score,actual_away_score,analysis_id)); return True
    def get_stats(self):
        total=(self.db.fetchone('SELECT COUNT(*) as count FROM analyses') or {'count':0})['count']; avg=(self.db.fetchone('SELECT AVG(confidence_score) as avg FROM analyses') or {'avg':0})['avg'] or 0; cached=(self.db.fetchone('SELECT COUNT(*) as count FROM analyses WHERE cached = 1') or {'count':0})['count']; by={r['sport']:r['count'] for r in self.db.fetchall('SELECT sport, COUNT(*) as count FROM analyses GROUP BY sport')}
        return {'total_analyses': total, 'average_confidence': round(avg,2), 'cached_percentage': round((cached/total*100) if total>0 else 0,2), 'by_sport': by}
_analysis_repo=None
def get_analysis_repo():
    global _analysis_repo
    if _analysis_repo is None: _analysis_repo=AnalysisRepository()
    return _analysis_repo
