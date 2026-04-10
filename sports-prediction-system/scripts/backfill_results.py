import sys
from pathlib import Path
project_root=Path(__file__).parent.parent; sys.path.insert(0,str(project_root))
from app.core.logging import setup_logging; setup_logging()
from app.storage.database import get_analysis_db
from app.storage.repositories.analysis_repo import get_analysis_repo
from app.clients.sofascore_client import get_sofascore_client

def determine_outcome(h,a): return 'home_win' if h>a else ('away_win' if a>h else 'draw')
def event_is_finished(event): return event.get('status',{}).get('type','').lower() in {'finished','afterpenalties','afterextratime'}
def extract_scores(event):
    hs=event.get('homeScore',{}).get('current'); a=event.get('awayScore',{}).get('current')
    return None if hs is None or a is None else {'home_score':int(hs),'away_score':int(a)}
def event_matches_analysis(event,home_team_id,away_team_id): return event.get('homeTeam',{}).get('id')==home_team_id and event.get('awayTeam',{}).get('id')==away_team_id
def find_best_finished_match(events,home_team_id,away_team_id,event_id=None):
    if event_id is not None:
        for event in events:
            if event.get('id')==event_id and event_is_finished(event): return event
    candidates=[e for e in events if event_matches_analysis(e,home_team_id,away_team_id) and event_is_finished(e)]
    if not candidates: return None
    candidates.sort(key=lambda e: e.get('startTimestamp',0), reverse=True); return candidates[0]
def main():
    pending=get_analysis_db().fetchall('SELECT id, home_team_id, away_team_id, event_id FROM analyses WHERE actual_outcome IS NULL AND home_team_id IS NOT NULL AND away_team_id IS NOT NULL ORDER BY created_at ASC')
    repo=get_analysis_repo(); client=get_sofascore_client(); updated=skipped=failed=0
    for row in pending:
        try:
            events=client.get_h2h_matches(row['home_team_id'],row['away_team_id']); match=find_best_finished_match(events,row['home_team_id'],row['away_team_id'],row.get('event_id')); scores=extract_scores(match) if match else None
            if not scores: skipped += 1; continue
            repo.update_actual_result(row['id'], determine_outcome(scores['home_score'],scores['away_score']), scores['home_score'], scores['away_score']); updated += 1
        except Exception: failed += 1
    print({'updated':updated,'skipped':skipped,'failed':failed})
if __name__=='__main__': main()
