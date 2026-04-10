class AppException(Exception):
    def __init__(self, message: str, code: str = 'INTERNAL_ERROR', details: dict | None = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)
    def to_dict(self):
        return {'error': {'code': self.code, 'message': self.message, 'details': self.details}}

class DatabaseError(AppException):
    def __init__(self, message, details=None):
        super().__init__(message, 'DATABASE_ERROR', details)
class TeamNotFoundError(AppException):
    def __init__(self, team_name, sport, competition):
        super().__init__(f"Team '{team_name}' not found", 'TEAM_NOT_FOUND', {'team_name': team_name, 'sport': sport, 'competition': competition})
class ValidationError(AppException):
    def __init__(self, field, message):
        super().__init__(f'Validation error: {field} - {message}', 'VALIDATION_ERROR', {'field': field, 'error': message})
class DuplicateTeamError(ValidationError):
    def __init__(self, team_name):
        super().__init__('teams', f"Home and away teams must be different (both are '{team_name}')")
class InsufficientDataError(AppException):
    def __init__(self, missing_data):
        super().__init__('Insufficient data for prediction', 'INSUFFICIENT_DATA', {'missing': missing_data})
class CircuitBreakerOpenError(AppException):
    def __init__(self, service):
        super().__init__(f'Circuit breaker is OPEN for {service}', 'CIRCUIT_BREAKER_OPEN', {'service': service})
