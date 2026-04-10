import math
from app.core.settings import settings
from app.prediction.base_engine import BasePredictionEngine
from app.prediction.confidence import calculate_confidence
class RuleEngineV2(BasePredictionEngine):
    def __init__(self):
        self.version='rule_v2'; self.weights={'form':settings.WEIGHT_FORM,'h2h':settings.WEIGHT_H2H,'home_advantage':settings.WEIGHT_HOME_ADVANTAGE,'stats':settings.WEIGHT_STATS,'xg':settings.WEIGHT_XG}
    def _calculate_home_score(self, f):
        score=0.0; score += self.weights['form'] * ((f.get('form_home',50)-f.get('form_away',50))/100); score += self.weights['h2h'] * ((f.get('h2h_home_ratio',0.5)-0.5)*2); score += self.weights['home_advantage'] * settings.HOME_ADVANTAGE_BONUS; score += self.weights['stats'] * ((f.get('stats_diff',0))/100)
        if f.get('xg_diff') is not None: score += self.weights['xg'] * f.get('xg_diff',0)
        return score
    def _scores_to_probabilities(self, hs,as_):
        shift=abs(min(hs,as_,0))+1; hs+=shift; as_+=shift; ds=shift; eh,ea,ed=math.exp(hs),math.exp(as_),math.exp(ds); total=eh+ea+ed; return {'home_win': round(eh/total,3), 'draw': round(ed/total,3), 'away_win': round(ea/total,3)}
    def predict(self, features):
        hs=self._calculate_home_score(features); as_=-hs + self.weights['home_advantage'] * settings.HOME_ADVANTAGE_BONUS; probs=self._scores_to_probabilities(hs,as_); outcome=max(probs,key=probs.get); conf=calculate_confidence(probs,float(features.get('data_quality',0.0))); factors=[]
        if features.get('form_home',50) > features.get('form_away',50) + 10: factors.append('home_form_advantage')
        elif features.get('form_away',50) > features.get('form_home',50) + 10: factors.append('away_form_advantage')
        if features.get('h2h_home_ratio',0.5) > 0.6: factors.append('positive_h2h')
        elif features.get('h2h_home_ratio',0.5) < 0.4: factors.append('negative_h2h')
        if hs > 0: factors.append('home_advantage')
        return {'outcome': outcome,'probabilities': probs,'confidence': conf,'factors': factors,'factor_weights': self.weights,'engine_version': self.version,'data_quality': float(features.get('data_quality',0.0)),'features': features,'balance_score': round(abs(sorted(probs.values(), reverse=True)[0]-sorted(probs.values(), reverse=True)[1]),4),'warnings': []}
_rule_engine_v2=None
def get_rule_engine_v2():
    global _rule_engine_v2
    if _rule_engine_v2 is None: _rule_engine_v2=RuleEngineV2()
    return _rule_engine_v2
