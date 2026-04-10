from datetime import datetime
from flask import Flask, jsonify, request, Response, render_template
from app.core.settings import settings
from app.storage.database import get_analysis_db, get_team_cache_db
from app.api.middleware import RequestIDMiddleware, get_current_request_id
from app.api.error_handlers import register_error_handlers
from app.core.metrics import get_metrics_registry
from app.services.analysis_service import get_analysis_service
from app.storage.repositories.analysis_repo import get_analysis_repo
from app.storage.repositories.team_repo import get_team_repo
from app.services.cache_service import get_cache_service
from app.prediction.ml_engine_v1 import get_ml_engine_v1
from app.clients.sofascore_client import get_sofascore_client

def _outcome_label(outcome):
    return {'home_win':'Home Win','draw':'Draw','away_win':'Away Win'}.get(outcome, outcome or 'Unknown')

def _safe_float(value, default=0.0):
    try: return float(value)
    except Exception: return default

def _build_accuracy_report(repo):
    rows=get_analysis_db().fetchall("""
        SELECT sport, competition, engine_version, prediction_outcome, actual_outcome, confidence_score
        FROM analyses
        WHERE actual_outcome IS NOT NULL
    """)
    total=len(rows)
    correct=sum(1 for r in rows if r['prediction_outcome']==r['actual_outcome'])
    by_sport={}
    by_engine={}
    confidence_buckets={'<50':{'total':0,'correct':0}, '50-69':{'total':0,'correct':0}, '70+':{'total':0,'correct':0}}
    for r in rows:
        sport=r['sport'] or 'unknown'
        by_sport.setdefault(sport, {'total':0,'correct':0})
        by_sport[sport]['total'] += 1
        by_sport[sport]['correct'] += int(r['prediction_outcome']==r['actual_outcome'])
        engine=r['engine_version'] or 'unknown'
        by_engine.setdefault(engine, {'total':0,'correct':0})
        by_engine[engine]['total'] += 1
        by_engine[engine]['correct'] += int(r['prediction_outcome']==r['actual_outcome'])
        conf=_safe_float(r.get('confidence_score'))
        bucket='<50' if conf < 50 else ('50-69' if conf < 70 else '70+')
        confidence_buckets[bucket]['total'] += 1
        confidence_buckets[bucket]['correct'] += int(r['prediction_outcome']==r['actual_outcome'])
    def finalize(mapping):
        return {k:{**v,'accuracy': round((v['correct']/v['total']*100),2) if v['total'] else None} for k,v in mapping.items()}
    return {
        'resolved_predictions': total,
        'overall_accuracy': round((correct/total*100),2) if total else None,
        'by_sport': finalize(by_sport),
        'by_engine': finalize(by_engine),
        'by_confidence_bucket': finalize(confidence_buckets)
    }

def create_app(config=None):
    app=Flask(__name__, template_folder='templates')
    app.config['JSON_SORT_KEYS']=False; app.json.ensure_ascii=False
    if config: app.config.update(config)
    RequestIDMiddleware(app); register_error_handlers(app)
    analysis_repo=get_analysis_repo(); analysis_service=get_analysis_service(); team_repo=get_team_repo(); sofascore_client=get_sofascore_client()

    @app.route('/')
    def index_html():
        try: return render_template('index.html')
        except Exception:
            return jsonify({'message': f'Welcome to {settings.APP_NAME} v{settings.APP_VERSION}','endpoints':{'health_live':'/health/live','health_ready':'/health/ready','metrics':'/metrics'}})

    @app.route('/health/live')
    def health_live(): return jsonify({'status':'ok','service':settings.APP_NAME,'version':settings.APP_VERSION,'environment':settings.ENVIRONMENT})

    @app.route('/health/ready')
    def health_ready():
        checks={'database': get_analysis_db().health_check(), 'team_cache': get_team_cache_db().health_check(), 'sofascore_api': True}
        core_ready=checks['database'] and checks['team_cache']
        return jsonify({'status':'ready' if core_ready else 'not_ready','checks':checks,'external_status':{'sofascore_available':checks['sofascore_api']}}), (200 if core_ready else 503)

    @app.route('/version')
    def version(): return jsonify({'app_name':settings.APP_NAME,'version':settings.APP_VERSION,'environment':settings.ENVIRONMENT,'prediction_engine':settings.PREDICTION_ENGINE})

    @app.route('/metrics')
    def metrics(): return Response(get_metrics_registry().render_prometheus(), mimetype='text/plain; version=0.0.4; charset=utf-8')

    @app.route('/api/test')
    def api_test():
        return jsonify({'success':True,'service':settings.APP_NAME,'version':settings.APP_VERSION,'request_id':get_current_request_id(),'status':'ok','rate_limit':{'enabled':settings.RATE_LIMIT_ENABLED,'per_minute':settings.RATE_LIMIT_PER_MINUTE},'available_endpoints':{'analyze':'/api/analyze','history':'/api/history','stats':'/api/stats','search':'/api/search','engine_status':'/api/engine-status','supported':'/api/supported','matches':'/api/matches','accuracy':'/api/accuracy-report','metrics':'/metrics'}})

    @app.route('/api/engine-status')
    def engine_status():
        ml=get_ml_engine_v1(); return jsonify({'success':True,'engine_requested':settings.PREDICTION_ENGINE,'engines':{'rule_v2':{'available':True},'ml_v1':{'available':ml.is_available(),'error':ml.get_load_error()}},'request_id':get_current_request_id()})

    @app.route('/api/supported')
    def supported():
        sport=request.args.get('sport','football')
        competition=request.args.get('competition','')
        rows=team_repo.get_all_for_sport(sport, competition)
        competitions=[c.strip() for c in settings.SUPPORTED_COMPETITIONS.split(',') if c.strip()]
        return jsonify({'success':True,'sport':sport,'competition':competition,'supported_competitions':competitions,'teams':[{'team_name':r['team_name'],'team_id':r['team_id'],'competition':r['competition']} for r in rows],'request_id':get_current_request_id()})

    @app.route('/api/matches')
    def matches():
        sport=request.args.get('sport','football')
        date_str=request.args.get('date') or datetime.utcnow().strftime('%Y-%m-%d')
        events=sofascore_client.get_scheduled_events_for_date(sport, date_str)
        competition=request.args.get('competition','').strip().lower()
        mapped=[]
        for e in events:
            tournament=((e.get('tournament') or {}).get('slug') or (e.get('tournament') or {}).get('name') or '')
            if competition and competition not in str(tournament).lower():
                continue
            mapped.append({
                'event_id': e.get('id'),
                'sport': sport,
                'competition': tournament,
                'home_team': (e.get('homeTeam') or {}).get('name'),
                'away_team': (e.get('awayTeam') or {}).get('name'),
                'home_team_id': (e.get('homeTeam') or {}).get('id'),
                'away_team_id': (e.get('awayTeam') or {}).get('id'),
                'scheduled_start_time': e.get('startTimestamp'),
                'status': ((e.get('status') or {}).get('type'))
            })
        return jsonify({'success':True,'sport':sport,'date':date_str,'count':len(mapped),'matches':mapped,'request_id':get_current_request_id()})

    @app.route('/api/analyze', methods=['POST'])
    def analyze():
        data=request.get_json(silent=True) or {}
        result=analysis_service.analyze(sport=data.get('sport',''),competition=data.get('competition',''),home_team=data.get('home_team',''),away_team=data.get('away_team',''),use_cache=bool(data.get('use_cache',True)),force_refresh=bool(data.get('force_refresh',False)))
        return jsonify(result)

    @app.route('/api/history')
    def history():
        limit=min(max(int(request.args.get('limit',10)),1),100)
        analyses=analysis_repo.get_recent(limit)
        for a in analyses:
            a['prediction_outcome_label']=_outcome_label(a.get('prediction_outcome'))
            if a.get('created_at'): a['created_at']=str(a['created_at']).replace(' ','T')
        return jsonify({'analyses':analyses})

    @app.route('/api/search')
    def search():
        limit=min(max(int(request.args.get('limit',10)),1),100); home_team=request.args.get('team','') or request.args.get('home_team',''); away_team=request.args.get('away_team','')
        results=analysis_repo.search_by_teams(home_team or None, away_team or None, limit)
        for r in results:
            r['prediction_outcome_label']=_outcome_label(r.get('prediction_outcome'))
            if r.get('created_at'): r['created_at']=str(r['created_at']).replace(' ','T')
        return jsonify({'results':results})

    @app.route('/api/accuracy-report')
    def accuracy_report():
        return jsonify({'success':True,'report':_build_accuracy_report(analysis_repo),'request_id':get_current_request_id()})

    @app.route('/api/stats')
    def get_stats():
        ml=get_ml_engine_v1()
        return jsonify({'success':True,'stats':{'analyses':analysis_repo.get_stats(),'cache':get_cache_service().get_stats(),'prediction':{'engine_requested':settings.PREDICTION_ENGINE,'ml_available':ml.is_available(),'ml_error':ml.get_load_error()}} ,'request_id':get_current_request_id()})
    return app
