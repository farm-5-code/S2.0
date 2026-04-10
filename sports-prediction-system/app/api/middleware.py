import uuid, time
from contextvars import ContextVar
from flask import request, g, jsonify
from app.core.logging import get_logger
from app.core.metrics import get_metrics_registry
from app.core.settings import settings
from app.api.rate_limiter import InMemoryRateLimiter
logger = get_logger(__name__)
metrics = get_metrics_registry()
request_id_context = ContextVar('request_id', default=None)
class RequestIDMiddleware:
    def __init__(self, app):
        self.app=app; self.rate_limiter=InMemoryRateLimiter(settings.RATE_LIMIT_PER_MINUTE); app.before_request(self.before_request); app.after_request(self.after_request)
    def _should_skip_rate_limit(self):
        return (request.path or '') in {'/health/live','/health/ready','/metrics'}
    def _get_client_key(self):
        xff=request.headers.get('X-Forwarded-For','').strip()
        if xff: return xff.split(',')[0].strip()
        xri=request.headers.get('X-Real-IP','').strip()
        if xri: return xri
        return request.remote_addr or 'unknown'
    def before_request(self):
        request_id=request.headers.get('X-Request-ID') or str(uuid.uuid4())
        g.request_id=request_id; request_id_context.set(request_id); g.request_start_time=time.time()
        metrics.inc('app_requests_total', labels={'method': request.method, 'path': request.path})
        if settings.RATE_LIMIT_ENABLED and not self._should_skip_rate_limit():
            allowed, remaining, reset_in = self.rate_limiter.check(self._get_client_key())
            g.rate_limit_limit=settings.RATE_LIMIT_PER_MINUTE; g.rate_limit_remaining=remaining; g.rate_limit_reset=reset_in
            if not allowed:
                metrics.inc('rate_limit_exceeded_total', labels={'path': request.path, 'method': request.method})
                metrics.inc('app_errors_total', labels={'error_code':'RATE_LIMIT_EXCEEDED'})
                response=jsonify({'error':{'code':'RATE_LIMIT_EXCEEDED','message':'Rate limit exceeded','details':{'limit_per_minute':settings.RATE_LIMIT_PER_MINUTE,'retry_after_seconds':reset_in}},'request_id':request_id})
                response.status_code=429; response.headers['Retry-After']=str(reset_in); response.headers['X-RateLimit-Limit']=str(settings.RATE_LIMIT_PER_MINUTE); response.headers['X-RateLimit-Remaining']='0'; response.headers['X-RateLimit-Reset']=str(reset_in)
                return response
            metrics.inc('rate_limit_allowed_total', labels={'path': request.path, 'method': request.method})
    @staticmethod
    def after_request(response):
        request_id=getattr(g,'request_id',None); start_time=getattr(g,'request_start_time',None)
        latency_ms=round((time.time()-start_time)*1000,2) if start_time else 0.0
        if request_id: response.headers['X-Request-ID']=request_id
        if hasattr(g,'rate_limit_limit'):
            response.headers['X-RateLimit-Limit']=str(g.rate_limit_limit); response.headers['X-RateLimit-Remaining']=str(g.rate_limit_remaining); response.headers['X-RateLimit-Reset']=str(g.rate_limit_reset)
        metrics.inc('app_responses_total', labels={'method': request.method, 'path': request.path, 'status_code': str(response.status_code)})
        metrics.observe_summary('app_request_latency_ms', latency_ms, labels={'method': request.method, 'path': request.path})
        return response

def get_current_request_id():
    return request_id_context.get()
