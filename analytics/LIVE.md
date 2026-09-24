# Live SQL logging

Ignition reads the 13 Feeder01 tags, heartbeat state/counter, and open-feedback
alarm condition/state approximately once per second. The Gateway appends daily
JSONL files in `analytics/live`. Python imports complete records into
`analytics/live/feeder-live.sqlite3` continuously. This is a local lab historian,
not an Ignition native historian or a Seeq integration.

The live database is separate from the synthetic demonstration database.
`snapshots` records observation time, LIVE source, heartbeat, missed-event flag
and acquisition gap; `readings` preserves each value, quality and source time.
`events` records initial observations and subsequent value/quality changes.
These are sampled changes: short pulses between samples may be missed, and a
multi-tag read is not an atomic PLC scan. Do not use this one-second stream for
subsecond breaker travel-time measurements. Bad quality and stale heartbeat must
be considered when interpreting recorded values.

## Run and check

From the project directory, with Python installed:

```powershell
python analytics/live_logger.py --watch
```

Omit `--watch` to catch up once. A Windows file lock prevents duplicate collectors.
Byte checkpoints and imported rows commit together; restarts resume without
duplicating records. Incomplete lines wait for completion, and invalid complete
lines are recorded in `rejects`. Never truncate the spool files.

```powershell
python analytics/live_status.py
```

The current background collector was started hidden using the bundled Python.
Its PID is in `analytics/live/logger.pid`; health is in `collector-status.json`.
Logs are `logger.stdout.log` and `logger.stderr.log`. It is not installed as a
Windows service and does not automatically restart after reboot. Ignition can
continue spooling while Python is offline; ingestion catches up when restarted.
Ignition trial expiration or a stopped Gateway interrupts acquisition.
Spool/database retention is manual; files grow while the lab runs.

## SQL examples

```sql
SELECT id, datetime(observed_ms/1000.0,'unixepoch') AS utc,
       heartbeat, gap_ms, missed_events
FROM snapshots ORDER BY id DESC LIMIT 20;

SELECT s.observed_ms, e.path, e.previous_json, e.value_json, e.quality, e.kind
FROM events e JOIN snapshots s ON s.id=e.snapshot_id
WHERE e.path LIKE '%Cmd_CB_%' OR e.path LIKE '%OpenFeedbackMissing%'
ORDER BY e.id DESC LIMIT 50;

SELECT s.observed_ms, r.path, r.value_json, r.quality, r.source_ms
FROM readings r JOIN snapshots s ON s.id=r.snapshot_id
WHERE r.good=0 OR s.heartbeat<>'ACTIVE'
ORDER BY s.id DESC LIMIT 50;
```

## Live analytics report

```powershell
python analytics/live_report.py
```

Open `analytics/output/live-report.html`. This report queries the LIVE database
read-only and includes observed command/output transitions, alarm activations,
heartbeat and quality counts, acquisition gaps, and recent event history. The
adjacent JSON contains the report data. Rerun the command to refresh the report;
it is a generated snapshot, not an automatically refreshing web application.

One-second acquisition can miss short pulses. Counts are observed transitions,
not guaranteed operation totals. The report does not apply the simulated
100 ms fixture's timing classifications or infer physical travel time.

Validated September 24, 2026: LIVE ingestion, zero rejected rows at inspection,
SQLite quick_check OK, increasing snapshot count and recent observations.
Historical acquisition gaps are retained. Alarm activation and clearing were
observed with manually simulated feedback; see the acceptance notes.
