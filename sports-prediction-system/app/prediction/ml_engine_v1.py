import numpy as np
from app.prediction.base_engine import BasePredictionEngine
from app.prediction.confidence import calculate_confidence
from app.prediction.model_loader import ModelLoader
class MLPredictionEngineV1(BasePredictionEngine):
    def __init__(self, loader=None): self.loader=loader or ModelLoader(); self._model=None; self._metadata=None; self._load_error=None; self._try_load()
    @property
    def version(self): return 'ml_v1'
    def _try_load(self):
        try: self._model,self._metadata=self.loader.load(); self._load_error=None
        except Exception as e: self._model=None; self._metadata=None; self._load_error=str(e)
    def is_available(self): return self._model is not None and self._metadata is not None
    def get_load_error(self): return self._load_error
    def _vectorize(self, features):
        return np.array([[float(features.get(name,0.0) or 0.0) for name in self._metadata['feature_order']]], dtype=float)
    def _normalize_probabilities(self, raw_probs):
        probs={'home_win':float(raw_probs.get('home_win',0.0)),'draw':float(raw_probs.get('draw',0.0)),'away_win':float(raw_probs.get('away_win',0.0))}; total=sum(probs.values())
        if total <= 0: return {'home_win':0.333,'draw':0.334,'away_win':0.333}
        probs={k:v/total for k,v in probs.items()}; rounded={k:round(v,3) for k,v in probs.items()}; drift=round(1.0-sum(rounded.values()),3); rounded['draw']=round(rounded['draw']+drift,3); return rounded
    def predict(self, features):
        if not self.is_available(): raise RuntimeError(f'ML model not available: {self._load_error}')
        probs=self._normalize_probabilities({label: float(prob) for label, prob in zip(self._metadata['class_order'], self._model.predict_proba(self._vectorize(features))[0])}); outcome=max(probs,key=probs.get); conf=calculate_confidence(probs,float(features.get('data_quality',0.0))); ordered=sorted(probs.values(), reverse=True)
        return {'outcome': outcome,'probabilities': probs,'confidence': conf,'factors': ['ml_model_v1'],'factor_weights': {},'engine_version': self.version,'data_quality': float(features.get('data_quality',0.0)),'features': features,'balance_score': round(ordered[0]-ordered[1],4),'warnings': []}
_ml_engine_v1=None
def get_ml_engine_v1():
    global _ml_engine_v1
    if _ml_engine_v1 is None: _ml_engine_v1=MLPredictionEngineV1()
    return _ml_engine_v1
