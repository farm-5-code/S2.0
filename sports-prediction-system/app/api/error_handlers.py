from flask import jsonify
from app.core.logging import get_logger
from app.core.exceptions import AppException
from app.api.middleware import get_current_request_id
from app.core.metrics import get_metrics_registry
logger=get_logger(__name__)
def register_error_handlers(app):
    metrics=get_metrics_registry()
    @app.errorhandler(AppException)
    def handle_app_exception(error):
        request_id=get_current_request_id(); metrics.inc('app_errors_total', labels={'error_code': error.code})
        status_map={'VALIDATION_ERROR':400,'TEAM_NOT_FOUND':404,'TEAM_NOT_FOUND_WITH_CANDIDATES':404,'NOT_FOUND':404,'INSUFFICIENT_DATA':422,'RATE_LIMIT_EXCEEDED':429,'CIRCUIT_BREAKER_OPEN':503,'EXTERNAL_API_ERROR':502,'DATABASE_ERROR':500,'CACHE_ERROR':500,'INVALID_PREDICTION':500}
        body=error.to_dict(); body['request_id']=request_id; return jsonify(body), status_map.get(error.code,400)
    @app.errorhandler(404)
    def h404(error): return jsonify({'error':{'code':'NOT_FOUND','message':'Endpoint not found','details':{}},'request_id':get_current_request_id()}),404
    @app.errorhandler(405)
    def h405(error): return jsonify({'error':{'code':'METHOD_NOT_ALLOWED','message':'Method not allowed','details':{}},'request_id':get_current_request_id()}),405
    @app.errorhandler(500)
    def h500(error): metrics.inc('app_errors_total', labels={'error_code':'INTERNAL_ERROR'}); return jsonify({'error':{'code':'INTERNAL_ERROR','message':'Internal server error','details':{}},'request_id':get_current_request_id()}),500
