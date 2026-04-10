#!/usr/bin/env python3
import sys
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
from app.core.settings import settings
from app.core.logging import setup_logging, get_logger
setup_logging()
logger = get_logger(__name__)
from app.web.app import create_app

def main():
    app = create_app()
    if settings.is_production:
        logger.error('Use gunicorn in production')
        sys.exit(1)
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG, use_reloader=False)

if __name__ == '__main__':
    main()
