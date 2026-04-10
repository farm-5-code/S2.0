import sys, json
from pathlib import Path
import pandas as pd
project_root=Path(__file__).parent.parent; sys.path.insert(0,str(project_root))
from app.storage.database import get_analysis_db
OUTPUT_PATH=Path('data/training_export.csv')
def main():
    db=get_analysis_db(); rows=db.fetchall('SELECT id, features_json, actual_outcome, engine_version, created_at FROM analyses WHERE actual_outcome IS NOT NULL ORDER BY created_at ASC'); records=[]
    for row in rows:
        try: features=json.loads(row['features_json']) if row.get('features_json') else None
        except Exception: features=None
        if not features: continue
        record={'analysis_id':row['id'],'actual_outcome':row['actual_outcome'],'engine_version':row['engine_version'],'created_at':row['created_at']}; record.update(features); records.append(record)
    df=pd.DataFrame(records); OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True); df.to_csv(OUTPUT_PATH,index=False); print(f'Exported {len(df)} rows to {OUTPUT_PATH}')
if __name__=='__main__': main()
