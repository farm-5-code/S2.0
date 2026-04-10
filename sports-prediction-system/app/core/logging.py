import logging, json, sys
from datetime import datetime
from pathlib import Path
from app.core.settings import settings

class JSONFormatter(logging.Formatter):
    def format(self, record):
        data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        for key in ['request_id','latency_ms','analysis_id','error_code','executed_function','status_code','path','method']:
            if hasattr(record, key):
                data[key] = getattr(record, key)
        if record.exc_info:
            data['exception'] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)

class TextFormatter(logging.Formatter):
    def __init__(self):
        super().__init__('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')

def setup_logging():
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.LOG_LEVEL))
    root.handlers.clear()
    formatter = JSONFormatter() if settings.LOG_FORMAT == 'json' else TextFormatter()
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    root.addHandler(sh)
    if settings.LOG_FILE:
        p = Path(settings.LOG_FILE)
        p.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(p, encoding='utf-8')
        fh.setFormatter(formatter)
        root.addHandler(fh)

def get_logger(name):
    return logging.getLogger(name)
