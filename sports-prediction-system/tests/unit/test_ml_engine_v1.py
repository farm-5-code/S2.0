from pathlib import Path
import joblib, numpy as np, pytest
from app.prediction.ml_engine_v1 import MLPredictionEngineV1
from app.prediction.model_loader import ModelLoader
class DummyModel:
    def predict_proba(self, X): return np.array([[0.52,0.21,0.27]])

def sample_features():
    return {'form_home':70.0,'form_away':55.0,'h2h_home_ratio':0.6,'home_advantage':1.0,'goals_scored_home':1.8,'goals_conceded_home':0.9,'goals_scored_away':1.2,'goals_conceded_away':1.1,'derived_stats_balance':12.0,'stats_diff':12.0,'xg_diff':0.0,'xg_available':0.0,'data_quality':0.8}

def write_test_model(tmp_path: Path):
    model_path=tmp_path/'model.joblib'; meta_path=tmp_path/'meta.json'; joblib.dump(DummyModel(), model_path); meta_path.write_text('{"model_version":"ml_v1","feature_order":["form_home","form_away","h2h_home_ratio","home_advantage","goals_scored_home","goals_conceded_home","goals_scored_away","goals_conceded_away","derived_stats_balance","stats_diff","xg_diff","xg_available","data_quality"],"class_order":["home_win","draw","away_win"]}', encoding='utf-8'); return model_path, meta_path

def test_ml_engine_predicts_expected_shape(tmp_path):
    mp, mt = write_test_model(tmp_path); engine=MLPredictionEngineV1(loader=ModelLoader(mp, mt)); result=engine.predict(sample_features()); assert result['engine_version']=='ml_v1'; assert result['outcome']=='home_win'

def test_ml_engine_unavailable_raises(tmp_path):
    engine=MLPredictionEngineV1(loader=ModelLoader(tmp_path/'missing.joblib', tmp_path/'missing.json')); assert engine.is_available() is False
    with pytest.raises(RuntimeError): engine.predict(sample_features())
