import sys, json
from pathlib import Path
project_root=Path(__file__).parent.parent; sys.path.insert(0,str(project_root))
from app.storage.database import get_analysis_db
from app.prediction.ml_engine_v1 import get_ml_engine_v1
OUTCOMES=['home_win','draw','away_win']
def safe_load_features(js):
    try: payload=json.loads(js); return {k: float(v or 0.0) for k,v in payload.items() if isinstance(v,(int,float)) or v is None}
    except Exception: return {}
def compute_accuracy(rows,predicted_field,actual_field):
    usable=[r for r in rows if r.get(predicted_field) is not None and r.get(actual_field) is not None]; return 0.0 if not usable else round(sum(1 for r in usable if r[predicted_field]==r[actual_field])/len(usable),4)
def compute_coverage(rows,predicted_field,actual_field):
    return 0.0 if not rows else round(len([r for r in rows if r.get(predicted_field) is not None and r.get(actual_field) is not None])/len(rows),4)
def build_confusion(rows,predicted_field,actual_field):
    m={a:{p:0 for p in OUTCOMES} for a in OUTCOMES}
    for r in rows:
        a=r.get(actual_field); p=r.get(predicted_field)
        if a in OUTCOMES and p in OUTCOMES: m[a][p]+=1
    return m
def evaluate_stored_engine(rows):
    return {'stored_prediction_accuracy': compute_accuracy(rows,'prediction_outcome','actual_outcome'),'stored_prediction_coverage': compute_coverage(rows,'prediction_outcome','actual_outcome'),'stored_prediction_confusion': build_confusion(rows,'prediction_outcome','actual_outcome'),'stored_accuracy_by_engine': {}}
def evaluate_ml_replay(rows):
    ml=get_ml_engine_v1()
    if not ml.is_available(): return {'ml_replay_available':False,'ml_replay_error':ml.get_load_error()}
    replay=[]; failed=0
    for row in rows:
        if row.get('actual_outcome') is None or not row.get('features_json'): continue
        features=safe_load_features(row['features_json'])
        if not features: failed += 1; continue
        try: replay.append({'actual_outcome': row['actual_outcome'], 'ml_outcome': ml.predict(features)['outcome']})
        except Exception: failed += 1
    return {'ml_replay_available':True,'ml_replay_rows':len(replay),'ml_replay_failed':failed,'ml_replay_coverage': round(len(replay)/len(rows),4) if rows else 0.0,'ml_replay_accuracy': compute_accuracy(replay,'ml_outcome','actual_outcome'),'ml_replay_confusion': build_confusion(replay,'ml_outcome','actual_outcome')}
def main():
    rows=get_analysis_db().fetchall('SELECT id, prediction_outcome, actual_outcome, engine_version, features_json FROM analyses WHERE actual_outcome IS NOT NULL ORDER BY created_at ASC')
    if not rows: print(json.dumps({'message':'No labeled analyses found. Backfill actual_outcome first.'}, indent=2)); return
    print(json.dumps({'labeled_rows': len(rows), **evaluate_stored_engine(rows), **evaluate_ml_replay(rows)}, indent=2))
if __name__=='__main__': main()
