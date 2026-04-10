from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = 'Sports Prediction System'
    APP_VERSION: str = '2.1.0'
    ENVIRONMENT: str = Field(default='development', pattern='^(development|staging|production)$')
    DEBUG: bool = False
    HOST: str = '0.0.0.0'
    PORT: int = Field(default=5000, ge=1, le=65535)
    WORKERS: int = Field(default=2, ge=1, le=16)
    DATABASE_URL: str = 'sqlite:///data/analysis.db'
    TEAM_CACHE_DB: str = 'sqlite:///data/team_cache.db'
    CACHE_DIR: str = 'cache'
    CACHE_TTL_HOURS: int = 6
    CACHE_VERSION: str = 'v2'
    SOFASCORE_BASE_URL: str = 'https://www.sofascore.com/api/v1'
    API_TIMEOUT: int = 3
    API_RETRY_COUNT: int = 1
    API_RETRY_BACKOFF: float = 0.2
    CB_FAILURE_THRESHOLD: int = 2
    CB_RECOVERY_TIMEOUT: int = 30
    PREDICTION_ENGINE: str = Field(default='rule_v2', pattern='^(rule_v2|ml_v1|ensemble_v1)$')
    WEIGHT_FORM: float = 0.35
    WEIGHT_H2H: float = 0.25
    WEIGHT_HOME_ADVANTAGE: float = 0.15
    WEIGHT_STATS: float = 0.15
    WEIGHT_XG: float = 0.10
    HOME_ADVANTAGE_BONUS: float = 0.10
    LOG_LEVEL: str = Field(default='INFO', pattern='^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$')
    LOG_FORMAT: str = Field(default='json', pattern='^(json|text)$')
    LOG_FILE: Optional[str] = 'logs/app.log'
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    METRICS_ENABLED: bool = True
    ALLOW_DEGRADED_PREDICTION: bool = True
    SUPPORTED_COMPETITIONS: str = 'epl,la_liga,serie_a,bundesliga,ligue_1,ucl'
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=True, extra='ignore')
    def validate_weights(self):
        total = self.WEIGHT_FORM + self.WEIGHT_H2H + self.WEIGHT_HOME_ADVANTAGE + self.WEIGHT_STATS + self.WEIGHT_XG
        if not (0.95 <= total <= 1.05):
            raise ValueError(f'Prediction weights must sum to ~1.0 (got {total:.2f})')
    @property
    def is_production(self):
        return self.ENVIRONMENT == 'production'

settings = Settings()
