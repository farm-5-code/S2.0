import sqlite3
from pathlib import Path
from contextlib import contextmanager
from app.core.settings import settings
from app.core.logging import get_logger
from app.core.exceptions import DatabaseError
logger=get_logger(__name__)
class Database:
    def __init__(self, db_url:str):
        self.db_url=db_url; self.db_path=self._parse_db_path(db_url); self.db_path.parent.mkdir(parents=True, exist_ok=True); self._init_schema()
    def _parse_db_path(self, db_url):
        if db_url.startswith('sqlite:///'): return Path(db_url.replace('sqlite:///', ''))
        raise ValueError(f'Invalid SQLite URL: {db_url}')
    def _init_schema(self):
        schema_file=Path(__file__).parent/'migrations'/'init_schema.sql'
        with open(schema_file,'r',encoding='utf-8') as f: schema_sql=f.read()
        with self.get_connection() as conn: conn.executescript(schema_sql)
    def get_connection(self):
        try:
            conn=sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0); conn.execute('PRAGMA foreign_keys = ON'); conn.row_factory=sqlite3.Row; return conn
        except Exception as e: raise DatabaseError(f'Connection failed: {e}')
    @contextmanager
    def transaction(self):
        conn=self.get_connection()
        try:
            yield conn; conn.commit()
        except Exception as e:
            conn.rollback(); raise DatabaseError(f'Transaction failed: {e}')
        finally:
            conn.close()
    def execute(self, query, params=()):
        with self.transaction() as conn:
            cur=conn.execute(query, params); return cur.lastrowid if cur.lastrowid else 0
    def fetchone(self, query, params=()):
        with self.get_connection() as conn:
            cur=conn.execute(query, params); row=cur.fetchone(); return dict(row) if row else None
    def fetchall(self, query, params=()):
        with self.get_connection() as conn:
            cur=conn.execute(query, params); return [dict(r) for r in cur.fetchall()]
    def get_schema_version(self):
        try:
            result=self.fetchone('SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1'); return result['version'] if result else None
        except Exception: return None
    def health_check(self):
        try:
            with self.get_connection() as conn: conn.execute('SELECT 1'); return True
        except Exception: return False
_analysis_db=None
_team_cache_db=None
def get_analysis_db():
    global _analysis_db
    if _analysis_db is None: _analysis_db=Database(settings.DATABASE_URL)
    return _analysis_db
def get_team_cache_db():
    global _team_cache_db
    if _team_cache_db is None: _team_cache_db=Database(settings.TEAM_CACHE_DB)
    return _team_cache_db
