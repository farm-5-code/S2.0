import requests
from app.core.settings import settings
from app.resilience.retry import RetryableError, NonRetryableError, classify_http_error, RetryStrategy
from app.resilience.circuit_breaker import CircuitBreaker
from app.resilience.timeout import TimeoutConfig
from app.api.middleware import get_current_request_id
class BaseHTTPClient:
    def __init__(self, base_url, service_name, timeout_config=None, enable_circuit_breaker=True):
        self.base_url=base_url.rstrip('/'); self.service_name=service_name; self.timeout_config=timeout_config or TimeoutConfig.default(); self.session=self._create_session(); self.circuit_breaker=CircuitBreaker(settings.CB_FAILURE_THRESHOLD, settings.CB_RECOVERY_TIMEOUT, name=service_name) if enable_circuit_breaker else None; self.retry_strategy=RetryStrategy(max_retries=settings.API_RETRY_COUNT, backoff_factor=settings.API_RETRY_BACKOFF, retryable_exceptions=(RetryableError, requests.Timeout, requests.ConnectionError))
    def _create_session(self):
        s=requests.Session(); s.headers.update({'User-Agent': f"{settings.APP_NAME}/{settings.APP_VERSION}", 'Accept': 'application/json'}); return s
    def _build_url(self, endpoint): return f"{self.base_url}/{endpoint.lstrip('/')}"
    def _handle_response(self, response):
        if response.status_code == 204: return {}
        if response.status_code < 400:
            try: return response.json()
            except ValueError as e: raise NonRetryableError(f'{self.service_name} returned non-JSON response with status {response.status_code}') from e
        if response.status_code == 429: raise RetryableError(f'{self.service_name} rate limit exceeded (429)')
        try: error_message=response.json().get('message', response.text)
        except Exception: error_message=response.text or f'HTTP {response.status_code}'
        error_class=classify_http_error(response.status_code)
        raise error_class(f'{self.service_name} returned {response.status_code}: {error_message}')
    def _execute_request(self, method, endpoint, params=None, json_data=None, headers=None):
        try:
            resp=self.session.request(method=method, url=self._build_url(endpoint), params=params, json=json_data, headers=headers, timeout=(self.timeout_config.connect,self.timeout_config.read))
            return self._handle_response(resp)
        except requests.Timeout as e: raise RetryableError(f'Request timeout after {self.timeout_config.total}s') from e
        except requests.ConnectionError as e: raise RetryableError(f'Connection error: {e}') from e
    def get(self, endpoint, params=None, headers=None):
        if self.circuit_breaker and self.circuit_breaker.get_state() == 'open': raise RuntimeError(f'{self.service_name} circuit breaker is open')
        if self.circuit_breaker: return self.circuit_breaker.call(self.retry_strategy.execute, self._execute_request, 'GET', endpoint, params=params, headers=headers)
        return self.retry_strategy.execute(self._execute_request, 'GET', endpoint, params=params, headers=headers)
    def post(self, endpoint, json_data=None, params=None, headers=None):
        if self.circuit_breaker and self.circuit_breaker.get_state() == 'open': raise RuntimeError(f'{self.service_name} circuit breaker is open')
        if self.circuit_breaker: return self.circuit_breaker.call(self.retry_strategy.execute, self._execute_request, 'POST', endpoint, params=params, json_data=json_data, headers=headers)
        return self.retry_strategy.execute(self._execute_request, 'POST', endpoint, params=params, json_data=json_data, headers=headers)
    def health_check(self):
        return not self.circuit_breaker or self.circuit_breaker.get_state() != 'open'
    def get_circuit_stats(self): return self.circuit_breaker.get_stats() if self.circuit_breaker else None
