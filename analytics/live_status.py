"""Read-only status of the LIVE SQLite logger."""
import json
from pathlib import Path
import sqlite3
import time

root = Path(__file__).resolve().parent / 'live'
db = sqlite3.connect((root / 'feeder-live.sqlite3').as_uri() + '?mode=ro', uri=True)
now = int(time.time()*1000)
latest = db.execute('SELECT observed_ms,heartbeat FROM snapshots ORDER BY id DESC LIMIT 1').fetchone()
result = {name: db.execute('SELECT COUNT(*) FROM ' + name).fetchone()[0]
          for name in ['snapshots', 'readings', 'events', 'rejects']}
result.update(latest_observation_ms=latest[0] if latest else None,
              observation_age_seconds=round((now-latest[0])/1000,1) if latest else None,
              heartbeat=latest[1] if latest else None,
              integrity=db.execute('PRAGMA quick_check').fetchone()[0],
              gaps_over_2500ms=db.execute('SELECT COUNT(*) FROM snapshots WHERE gap_ms>2500 OR gap_ms<=0').fetchone()[0])
status = root / 'collector-status.json'
if status.exists():
    collector = json.loads(status.read_text())
    result['collector_pid'] = collector['pid']
    result['collector_check_age_seconds'] = round((now-collector['checked_ms'])/1000,1)
print(json.dumps(result,indent=2))
db.close()
