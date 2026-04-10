from pathlib import Path
import json, joblib, pytest
from app.prediction.model_loader import ModelLoader
class DummyModel: pass

def test_model_loader_exists_true(tmp_path: Path):
    model_path=tmp_path/'model.joblib'; meta_path=tmp_path/'meta.json'; joblib.dump(DummyModel(), model_path); meta_path.write_text(json.dumps({'feature_order':['a','b'],'class_order':['home_win','draw','away_win']}), encoding='utf-8'); loader=ModelLoader(model_path=model_path, meta_path=meta_path); assert loader.exists() is True

def test_model_loader_raises_if_model_missing(tmp_path: Path):
    meta_path=tmp_path/'meta.json'; meta_path.write_text(json.dumps({'feature_order':['a'],'class_order':['home_win','draw','away_win']}), encoding='utf-8'); loader=ModelLoader(model_path=tmp_path/'missing.joblib', meta_path=meta_path)
    with pytest.raises(FileNotFoundError): loader.load()
