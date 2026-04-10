import sys, json, joblib, pandas as pd
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
project_root=Path(__file__).parent.parent; sys.path.insert(0,str(project_root))
from app.storage.database import get_analysis_db
MODEL_DIR=Path('models'); MODEL_PATH=MODEL_DIR/'model_v1.joblib'; META_PATH=MODEL_DIR/'model_meta_v1.json'
FEATURE_ORDER=['form_home','form_away','h2h_home_ratio','home_advantage','goals_scored_home','goals_conceded_home','goals_scored_away','goals_conceded_away','derived_stats_balance','stats_diff','xg_diff','xg_available','data_quality']
CLASS_ORDER=['home_win','draw','away_win']
def load_training_frame():
    rows=get_analysis_db().fetchall('SELECT features_json, actual_outcome FROM analyses WHERE actual_outcome IS NOT NULL AND features_json IS NOT NULL'); records=[]
    for row in rows:
        try: features=json.loads(row['features_json'])
        except Exception: continue
        rec={name: float(features.get(name,0.0) or 0.0) for name in FEATURE_ORDER}; rec['actual_outcome']=row['actual_outcome']; records.append(rec)
    return pd.DataFrame(records)
def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True); df=load_training_frame();
    if df.empty: raise RuntimeError('No training data found. Need analyses with actual_outcome.')
    df=df[df['actual_outcome'].isin(CLASS_ORDER)].copy(); df=df[df['data_quality']>=0.30].copy()
    for col in ['form_home','form_away','h2h_home_ratio','home_advantage','stats_diff','data_quality']: df=df[df[col].notna()].copy()
    class_counts=df['actual_outcome'].value_counts().to_dict(); print('Class distribution:', class_counts)
    if len(class_counts)<2 or len(df)<20: raise RuntimeError(f'Not enough labeled data to train model. Need ~20+, got {len(df)}.')
    X=df[FEATURE_ORDER]; y=df['actual_outcome']; X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=0.25,random_state=42,stratify=y); model=LogisticRegression(max_iter=1000,multi_class='multinomial'); model.fit(X_train,y_train); report=classification_report(y_test,model.predict(X_test),output_dict=True)
    joblib.dump(model,MODEL_PATH); META_PATH.write_text(json.dumps({'model_version':'ml_v1','feature_order':FEATURE_ORDER,'class_order':CLASS_ORDER,'train_rows':int(len(X_train)),'test_rows':int(len(X_test)),'metrics':report},ensure_ascii=False,indent=2),encoding='utf-8'); print(f'Saved model to {MODEL_PATH}'); print(f'Saved metadata to {META_PATH}')
if __name__=='__main__': main()
