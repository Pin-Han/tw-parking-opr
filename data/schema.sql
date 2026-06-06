CREATE TABLE IF NOT EXISTS snapshots (
    id              SERIAL PRIMARY KEY,
    source          TEXT NOT NULL,
    road_id         TEXT NOT NULL,
    road_name       TEXT,
    district        TEXT,
    total_spots     INTEGER,
    available_spots INTEGER,
    usage_rate      REAL,
    snapshot_time   TIMESTAMP NOT NULL,
    hour            INTEGER,
    day_of_week     INTEGER,
    is_weekend      INTEGER,
    is_holiday      INTEGER DEFAULT 0,
    weather_main    TEXT,
    latitude        REAL,
    longitude       REAL
);

CREATE TABLE IF NOT EXISTS opr_daily (
    id              SERIAL PRIMARY KEY,
    date            TEXT NOT NULL,
    district        TEXT NOT NULL,
    avg_usage_rate  REAL,
    peak_usage_rate REAL,
    peak_hour       INTEGER,
    min_usage_rate  REAL,
    off_peak_hour   INTEGER,
    is_holiday      INTEGER,
    weather_main    TEXT,
    UNIQUE(date, district)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_time ON snapshots(snapshot_time);
CREATE INDEX IF NOT EXISTS idx_snapshots_district_hour ON snapshots(district, hour, day_of_week);
CREATE INDEX IF NOT EXISTS idx_opr_daily_date ON opr_daily(date, district);
