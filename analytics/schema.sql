PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    created_utc TEXT NOT NULL,
    source TEXT NOT NULL CHECK(source IN ('SIMULATED', 'LIVE')),
    description TEXT NOT NULL
);
-- UTC Unix milliseconds. Each row is one coherent acquisition of these tags.
CREATE TABLE IF NOT EXISTS samples (
    run_id INTEGER NOT NULL REFERENCES runs(id),
    timestamp_ms INTEGER NOT NULL,
    feeder TEXT NOT NULL,
    quality TEXT NOT NULL CHECK(quality IN ('GOOD', 'BAD')),
    cmd_close INTEGER NOT NULL CHECK(cmd_close IN (0,1)),
    cmd_open INTEGER NOT NULL CHECK(cmd_open IN (0,1)),
    cb_open INTEGER NOT NULL CHECK(cb_open IN (0,1)),
    PRIMARY KEY(run_id, feeder, timestamp_ms)
);
CREATE TABLE IF NOT EXISTS operations (
    run_id INTEGER NOT NULL REFERENCES runs(id),
    feeder TEXT NOT NULL,
    command_ms INTEGER NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('CLOSE', 'OPEN')),
    response_ms INTEGER,
    outcome TEXT NOT NULL,
    PRIMARY KEY(run_id, feeder, command_ms, direction)
);
CREATE VIEW IF NOT EXISTS operation_summary AS
SELECT run_id, feeder, direction, outcome, COUNT(*) AS operation_count,
       AVG(response_ms) AS mean_response_ms, MAX(response_ms) AS max_response_ms
FROM operations GROUP BY run_id, feeder, direction, outcome;
