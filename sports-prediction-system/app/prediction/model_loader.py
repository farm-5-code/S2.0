from pathlib import Path
import json, joblib
DEFAULT_MODEL_PATH = Path('models/model_v1.joblib')
DEFAULT_META_PATH = Path('models/model_meta_v1.json')
class ModelLoader:
    def __init__(self, model_path=DEFAULT_MODEL_PATH, meta_path=DEFAULT_META_PATH): self.model_path=Path(model_path); self.meta_path=Path(meta_path)
    def exists(self): return self.model_path.exists() and self.meta_path.exists()
    def load(self):
        if not self.model_path.exists(): raise FileNotFoundError(f'Model file not found: {self.model_path}')
        if not self.meta_path.exists(): raise FileNotFoundError(f'Model metadata file not found: {self.meta_path}')
        model=joblib.load(self.model_path)
        with open(self.meta_path,'r',encoding='utf-8') as f: meta=json.load(f)
        if 'feature_order' not in meta: raise ValueError("Model metadata missing 'feature_order'")
        if 'class_order' not in meta: raise ValueError("Model metadata missing 'class_order'")
        return model, meta
