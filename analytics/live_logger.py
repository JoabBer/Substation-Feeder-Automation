"""Ingest read-only Ignition Gateway snapshots into a separate LIVE SQLite DB.

No PLC writes or network listener. Byte checkpoints commit with rows; incomplete
last lines are retried. A restart does not duplicate already imported events.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import time
import os
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parent / 'live'

@contextmanager
def collector_lock(directory):
    """One collector per spool, released automatically if the process exits."""
    import msvcrt
    with (Path(directory) / 'collector.lock').open('a+b') as lock:
        if lock.tell() == 0:
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError('A collector is already running for this directory')
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)

def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.executescript('''
    PRAGMA journal_mode=WAL;
    PRAGMA foreign_keys=ON;
    CREATE TABLE IF NOT EXISTS checkpoints(file TEXT PRIMARY KEY, offset INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS snapshots(
      id INTEGER PRIMARY KEY, file TEXT NOT NULL, byte_offset INTEGER NOT NULL,
      observed_ms INTEGER NOT NULL, source TEXT NOT NULL CHECK(source='LIVE'),
      heartbeat TEXT, missed_events INTEGER NOT NULL, gap_ms INTEGER,
      UNIQUE(file, byte_offset));
    CREATE TABLE IF NOT EXISTS readings(
      snapshot_id INTEGER REFERENCES snapshots(id), path TEXT NOT NULL,
      value_json TEXT, quality TEXT NOT NULL, good INTEGER NOT NULL,
      source_ms INTEGER NOT NULL, PRIMARY KEY(snapshot_id,path));
    CREATE TABLE IF NOT EXISTS events(
      id INTEGER PRIMARY KEY, snapshot_id INTEGER REFERENCES snapshots(id),
      path TEXT NOT NULL, previous_json TEXT, value_json TEXT, quality TEXT NOT NULL,
      kind TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS latest(path TEXT PRIMARY KEY, value_json TEXT, quality TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS rejects(file TEXT, byte_offset INTEGER, reason TEXT, PRIMARY KEY(file,byte_offset));
    ''')
    return db

def ingest(db, directory):
    count = 0
    for path in sorted(Path(directory).glob('snapshots-*.jsonl')):
        key = str(path.resolve())
        checkpoint = db.execute('SELECT offset FROM checkpoints WHERE file=?', (key,)).fetchone()
        offset = checkpoint[0] if checkpoint else 0
        if path.stat().st_size < offset:
            raise RuntimeError('Spool was truncated: ' + key)
        with path.open('rb') as stream:
            stream.seek(offset)
            while True:
                start = stream.tell()
                line = stream.readline()
                if not line or not line.endswith(b'\n'):
                    break
                with db:
                    try:
                        row = json.loads(line)
                        assert row['schema'] == 1 and row['source'] == 'LIVE'
                        assert isinstance(row['observed_ms'], int)
                        tags = row['tags']
                        assert tags and len({t['path'] for t in tags}) == len(tags)
                        for tag in tags:
                            assert isinstance(tag['good'], bool)
                            assert isinstance(tag['timestamp_ms'], int)
                            assert isinstance(tag['quality'], str)
                            assert isinstance(tag['path'], str)
                            tag['value']
                    except (ValueError, KeyError, TypeError, AssertionError) as exc:
                        db.execute('INSERT OR IGNORE INTO rejects VALUES (?,?,?)', (key, start, str(exc) or 'Invalid snapshot'))
                    else:
                        prev = db.execute('SELECT observed_ms FROM snapshots ORDER BY id DESC LIMIT 1').fetchone()
                        gap = row['observed_ms'] - prev[0] if prev else None
                        heartbeat = next((t['value'] for t in tags if t['path'] == '[default]FeederDiagnostics/State' and t['good']), 'UNKNOWN')
                        sid = db.execute('INSERT INTO snapshots(file,byte_offset,observed_ms,source,heartbeat,missed_events,gap_ms) VALUES (?,?,?,?,?,?,?)',
                            (key, start, row['observed_ms'], 'LIVE', heartbeat, bool(row.get('missed_events')), gap)).lastrowid
                        for tag in tags:
                            value = json.dumps(tag['value'], sort_keys=True)
                            db.execute('INSERT INTO readings VALUES (?,?,?,?,?,?)', (sid, tag['path'], value, tag['quality'], tag['good'], tag['timestamp_ms']))
                            old = db.execute('SELECT value_json,quality FROM latest WHERE path=?', (tag['path'],)).fetchone()
                            if old is None or old != (value, tag['quality']):
                                db.execute('INSERT INTO events(snapshot_id,path,previous_json,value_json,quality,kind) VALUES (?,?,?,?,?,?)',
                                    (sid, tag['path'], old[0] if old else None, value, tag['quality'], 'INITIAL' if old is None else 'CHANGE'))
                            db.execute('INSERT OR REPLACE INTO latest VALUES (?,?,?)', (tag['path'],value,tag['quality']))
                        count += 1
                    db.execute('INSERT OR REPLACE INTO checkpoints VALUES (?,?)', (key, stream.tell()))
    return count

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=ROOT)
    parser.add_argument('--watch', action='store_true')
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    with collector_lock(args.directory):
        db = connect(args.directory / 'feeder-live.sqlite3')
        try:
            while True:
                count = ingest(db, args.directory)
                status = dict(pid=os.getpid(), checked_ms=int(time.time()*1000),
                    snapshots=db.execute('SELECT COUNT(*) FROM snapshots').fetchone()[0],
                    latest_ms=db.execute('SELECT MAX(observed_ms) FROM snapshots').fetchone()[0])
                temp = args.directory / 'collector-status.tmp'
                temp.write_text(json.dumps(status), encoding='utf-8')
                temp.replace(args.directory / 'collector-status.json')
                if count: print('Imported %d snapshots' % count, flush=True)
                if not args.watch: break
                time.sleep(1)
        finally:
            db.close()

if __name__ == '__main__': main()
