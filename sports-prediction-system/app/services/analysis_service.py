import time
from app.core.logging import get_logger
from app.core.settings import settings
from app.core.exceptions import ValidationError, DuplicateTeamError, InsufficientDataError
from app.core.metrics import get_metrics_registry
from app.services.team_resolver import get_team_resolver
from app.services.data_collector import get_data_collector
from app.services.feature_service import get_feature_service
from app.storage.repositories.analysis_repo import get_analysis_repo
from app.prediction.rule_engine_v2 import get_rule_engine_v2
from app.prediction.ml_engine_v1 import get_ml_engine_v1
from app.clients.sofascore_client import get_sofascore_client
from app.api.middleware import get_current_request_id
logger=get_logger(__name__)

class AnalysisService:
    def __init__(self):
        self.team_resolver=get_team_resolver(); self.data_collector=get_data_collector(); self.feature_service=get_feature_service(); self.analysis_repo=get_analysis_repo(); self.rule_engine=get_rule_engine_v2(); self.ml_engine=get_ml_engine_v1(); self.sofascore_client=get_sofascore_client(); self.metrics=get_metrics_registry()

    def _validate_input(self,sport,competition,home_team,away_team):
        if not sport: raise ValidationError('sport','Sport is required')
        if not competition: raise ValidationError('competition','Competition is required')
        if not home_team: raise ValidationError('home_team','Home team is required')
        if not away_team: raise ValidationError('away_team','Away team is required')
        if home_team.lower().strip() == away_team.lower().strip(): raise DuplicateTeamError(home_team)

    def _build_missing_data_list(self,match_data):
        missing=[]
        if not match_data.get('home_team_stats') and not match_data.get('away_team_stats'): missing.append('team_statistics')
        if not match_data.get('home_recent') and not match_data.get('away_recent'): missing.append('recent_form')
        if not match_data.get('h2h'): missing.append('h2h_records')
        return missing

    def _data_quality_band(self, score):
        if score >= 0.85: return 'high'
        if score >= 0.60: return 'medium'
        if score >= 0.35: return 'low'
        return 'degraded'

    def _build_quality_summary(self, score, missing):
        band=self._data_quality_band(score)
        message_map={
            'high':'Strong data coverage; prediction is based on recent form and match context.',
            'medium':'Usable data coverage; treat the prediction as directional rather than definitive.',
            'low':'Partial data coverage; prediction may miss important factors.',
            'degraded':'Very limited data coverage; fallback logic was used.'
        }
        return {'score': round(float(score),2), 'band': band, 'missing_factors': missing, 'message': message_map[band]}

    def _build_degraded_prediction(self, features):
        return {'outcome':'draw','probabilities':{'home_win':0.318,'draw':0.364,'away_win':0.318},'confidence':30.0,'factors':['low_data_quality_fallback'],'factor_weights':{},'engine_version':'fallback_v1','data_quality':float(features.get('data_quality',0.0)),'features':features,'balance_score':0.0,'warnings':[{'code':'LOW_DATA_QUALITY','message':'Prediction generated from degraded fallback mode'}]}

    def _predict_with_selected_engine(self, features):
        req=settings.PREDICTION_ENGINE
        if req == 'ml_v1':
            if self.ml_engine.is_available():
                try: return self.ml_engine.predict(features)
                except Exception: self.metrics.inc('prediction_fallback_total', labels={'from_engine':'ml_v1','to_engine':'rule_v2'}); return self.rule_engine.predict(features)
            self.metrics.inc('prediction_fallback_total', labels={'from_engine':'ml_v1','to_engine':'rule_v2'}); return self.rule_engine.predict(features)
        if req == 'ensemble_v1':
            self.metrics.inc('prediction_fallback_total', labels={'from_engine':'ensemble_v1','to_engine':'rule_v2'}); return self.rule_engine.predict(features)
        return self.rule_engine.predict(features)

    def _find_match_context(self,sport,home_team_id,away_team_id):
        try:
            event=self.sofascore_client.find_scheduled_match(sport,home_team_id,away_team_id)
            if not event: return {'event_id':None,'scheduled_start_time':None}
            ts=event.get('startTimestamp'); return {'event_id': event.get('id'), 'scheduled_start_time': str(ts) if ts is not None else None}
        except Exception: return {'event_id':None,'scheduled_start_time':None}

    def analyze(self,sport,competition,home_team,away_team,use_cache=True,force_refresh=False):
        request_id=get_current_request_id(); started=time.time(); self._validate_input(sport,competition,home_team,away_team)
        home_team_id=self.team_resolver.resolve(home_team,sport,competition); away_team_id=self.team_resolver.resolve(away_team,sport,competition)
        match_context=self._find_match_context(sport,home_team_id,away_team_id)
        match_data, from_cache=self.data_collector.collect(home_team_id,away_team_id,sport,use_cache,force_refresh)
        data_quality=float(match_data.get('data_quality',0.0))
        missing=self._build_missing_data_list(match_data)
        if data_quality < 0.2:
            if not settings.ALLOW_DEGRADED_PREDICTION: raise InsufficientDataError(missing)
            features=self.feature_service.extract(match_data,home_team,away_team); prediction=self._build_degraded_prediction(features)
        else:
            features=self.feature_service.extract(match_data,home_team,away_team); prediction=self._predict_with_selected_engine(features)
        if 'warnings' not in prediction: prediction['warnings']=[]
        quality=self._build_quality_summary(data_quality, missing)
        if quality['band'] in {'low','degraded'} and not any(w.get('code')=='LOW_DATA_QUALITY' for w in prediction['warnings']):
            prediction['warnings'].append({'code':'LOW_DATA_QUALITY','message':quality['message']})
        self.metrics.inc('predictions_total', labels={'engine_used': prediction['engine_version']})
        self.metrics.inc('prediction_outcomes_total', labels={'outcome': prediction['outcome'], 'engine_used': prediction['engine_version']})
        analysis_id=self.analysis_repo.save(
            sport=sport,competition=competition,home_team=home_team,away_team=away_team,home_team_id=home_team_id,away_team_id=away_team_id,
            prediction_outcome=prediction['outcome'],home_win_probability=prediction['probabilities']['home_win'],draw_probability=prediction['probabilities']['draw'],
            away_win_probability=prediction['probabilities']['away_win'],confidence_score=prediction['confidence'],engine_version=prediction['engine_version'],
            engine_factors=prediction['factors'],features=features,data_quality_score=data_quality,cached=from_cache,request_id=request_id,event_id=match_context['event_id'],
            scheduled_start_time=match_context['scheduled_start_time'],analysis_source='api'
        )
        latency_ms=round((time.time()-started)*1000,2)
        self.metrics.inc('analyses_total', labels={'sport':sport,'competition':competition})
        self.metrics.observe_summary('analysis_latency_ms', latency_ms, labels={'sport':sport,'engine_used':prediction['engine_version']})
        return {
            'success': True,
            'analysis_id':analysis_id,'sport':sport,'competition':competition,'home_team':home_team,'away_team':away_team,'home_team_id':home_team_id,'away_team_id':away_team_id,
            'event_id':match_context['event_id'],'scheduled_start_time':match_context['scheduled_start_time'],'prediction':prediction,'features':features,'data_quality':data_quality,
            'data_quality_summary': quality, 'warnings': prediction.get('warnings', []), 'cached':from_cache,'request_id':request_id,'engine_requested':settings.PREDICTION_ENGINE,'engine_used':prediction['engine_version'],
            'latency_ms': latency_ms
        }

_analysis_service=None
def get_analysis_service():
    global _analysis_service
    if _analysis_service is None: _analysis_service=AnalysisService()
    return _analysis_service
