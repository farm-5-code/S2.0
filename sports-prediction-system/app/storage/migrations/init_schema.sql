CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sport TEXT NOT NULL,
    competition TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_team_id INTEGER,
    away_team_id INTEGER,
    event_id INTEGER,
    scheduled_start_time TEXT,
    prediction_outcome TEXT,
    home_win_probability REAL,
    draw_probability REAL,
    away_win_probability REAL,
    confidence_score REAL,
    engine_version TEXT NOT NULL DEFAULT 'rule_v2',
    engine_factors TEXT,
    features_json TEXT,
    data_quality_score REAL,
    cached BOOLEAN DEFAULT 0,
    request_id TEXT,
    analysis_source TEXT DEFAULT 'manual',
    actual_outcome TEXT,
    actual_home_score INTEGER,
    actual_away_score INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at DESC);
CREATE TABLE IF NOT EXISTS team_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_name TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    sport TEXT NOT NULL,
    competition TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    last_verified TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aliases TEXT,
    UNIQUE(team_name, sport, competition)
);
CREATE TABLE IF NOT EXISTS schema_version (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO schema_version(version) VALUES ('2.0.0');
