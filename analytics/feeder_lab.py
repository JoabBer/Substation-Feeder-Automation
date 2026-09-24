"""Offline feeder historian and response analysis. Python standard library only."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent
SLOW_MS = 500
TIMEOUT_MS = 2000
MAX_GAP_MS = 150


def connect(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript((ROOT / 'schema.sql').read_text())
    return db


def simulate(db):
    """Generate 100 close requests plus return-to-open requests at 100 ms cadence."""
    run = db.execute('INSERT INTO runs(created_utc,source,description) VALUES (?,?,?)',
                     (datetime.now(timezone.utc).isoformat(), 'SIMULATED',
                      '100 close requests; deterministic synthetic feeder fixture')).lastrowid
    start = 1789516800000
    slow = {12, 29, 47, 68, 91}
    failed = {35, 80}
    unknown = {55, 95}
    rows = []
    for number in range(1, 101):
        base = start + (number - 1) * 8000
        delay = 900 if number in slow else 200 + (number % 3) * 100
        for offset in range(0, 8000, 100):
            closed = number not in failed and 1000 + delay <= offset < 4300
            quality = 'BAD' if number in unknown and 1100 <= offset <= 1600 else 'GOOD'
            rows.append((run, base + offset, 'Feeder01', quality,
                         int(1000 <= offset < 1500),
                         int(number not in failed and 4000 <= offset < 4500),
                         int(not closed)))
    db.executemany('INSERT INTO samples VALUES (?,?,?,?,?,?,?)', rows)
    db.commit()
    return run


def classify(samples, slow_ms=SLOW_MS, timeout_ms=TIMEOUT_MS, max_gap_ms=MAX_GAP_MS):
    """Analyze one feeder's sorted coherent samples without consulting scenario truth.

    Measure request rising edge to first target-position feedback. Missing data,
    unknown initial command state, and unfinished windows cannot prove failure.
    A subsequent request ends an outstanding request to prevent cross-pairing.
    """
    results = []
    previous = None
    pending = None

    def finish(outcome, response=None):
        nonlocal pending
        results.append(dict(command_ms=pending['time'], direction=pending['direction'],
                            response_ms=response, outcome=outcome))
        pending = None

    for row in samples:
        now = row['timestamp_ms']
        if previous is not None and now <= previous['timestamp_ms']:
            raise ValueError('Samples must have strictly increasing timestamps')
        good = row['quality'] == 'GOOD'
        continuous = (previous is not None and previous['quality'] == 'GOOD'
                      and good and now - previous['timestamp_ms'] <= max_gap_ms)
        if pending:
            elapsed = now - pending['time']
            if not continuous:
                finish('UNKNOWN_DATA')
            elif elapsed > timeout_ms:
                # Previous observation must cover the deadline to prove a timeout.
                finish('NO_FEEDBACK' if previous['timestamp_ms'] >= pending['time'] + timeout_ms
                       else 'UNKNOWN_DATA')
        edges = []
        if good:
            for field, direction in [('cmd_close', 'CLOSE'), ('cmd_open', 'OPEN')]:
                if row[field] and (not continuous or not previous[field]):
                    edges.append(direction)
        if edges and pending:
            finish('SUPERSEDED')
        for direction in edges:
            pending = dict(time=now, direction=direction)
            target = 0 if direction == 'CLOSE' else 1
            if not continuous:
                finish('UNKNOWN_START')
            elif row['cmd_close'] and row['cmd_open']:
                finish('CONFLICTING_COMMANDS')
            elif previous['cb_open'] == target:
                finish('ALREADY_AT_TARGET')
        if pending:
            elapsed = now - pending['time']
            target = 0 if pending['direction'] == 'CLOSE' else 1
            if row['cb_open'] == target:
                finish('SLOW' if elapsed > slow_ms else 'NORMAL', elapsed)
            elif elapsed >= timeout_ms:
                finish('NO_FEEDBACK')
        previous = row
    if pending:
        finish('INCOMPLETE')
    return results


def analyze(db, run):
    db.execute('DELETE FROM operations WHERE run_id=?', (run,))
    feeders = [r[0] for r in db.execute('SELECT DISTINCT feeder FROM samples WHERE run_id=?', (run,))]
    for feeder in feeders:
        samples = db.execute('SELECT * FROM samples WHERE run_id=? AND feeder=? ORDER BY timestamp_ms',
                             (run, feeder)).fetchall()
        for result in classify(samples):
            db.execute('INSERT INTO operations VALUES (?,?,?,?,?,?)',
                       (run, feeder, result['command_ms'], result['direction'],
                        result['response_ms'], result['outcome']))
    db.commit()


def report(db, run, directory):
    info = dict(db.execute('SELECT * FROM runs WHERE id=?', (run,)).fetchone())
    operations = [dict(r) for r in db.execute(
        'SELECT * FROM operations WHERE run_id=? ORDER BY command_ms,feeder,direction', (run,))]
    summary = [dict(r) for r in db.execute('SELECT * FROM operation_summary WHERE run_id=?', (run,))]
    data = dict(run=info, thresholds=dict(slow_ms=SLOW_MS, timeout_ms=TIMEOUT_MS,
                                        maximum_sample_gap_ms=MAX_GAP_MS), summary=summary, operations=operations)
    (directory / 'report.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    close_counts = Counter(r['outcome'] for r in operations if r['direction'] == 'CLOSE')
    cards = ''.join(f'<article><strong>{close_counts[key]}</strong>{label}</article>' for key, label in
                    [('NORMAL', 'Normal closes'), ('SLOW', 'Slow closes'),
                     ('NO_FEEDBACK', 'Missing close feedback'), ('UNKNOWN_DATA', 'Uncertain closes')])
    rows = ''.join('<tr>' + ''.join(f'<td>{html.escape(str(value))}</td>' for value in
                  [datetime.fromtimestamp(r['command_ms']/1000, timezone.utc).isoformat(), r['feeder'],
                   r['direction'], r['outcome'], r['response_ms'] if r['response_ms'] is not None else '—'])
                   + '</tr>' for r in operations)
    closes = [r for r in operations if r['direction'] == 'CLOSE']
    bars = ''.join(f'<rect x="{i*9+45}" y="{220-r["response_ms"]/5}" width="6" '
                   f'height="{r["response_ms"]/5}" fill="{"#f3bc56" if r["outcome"] == "SLOW" else "#53ceb2"}">'
                   f'<title>Close {i+1}: {r["response_ms"]} ms</title></rect>'
                   for i, r in enumerate(closes) if r['response_ms'] is not None)
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Feeder analytics lab</title>
<style>body{font:16px system-ui;background:#101c2c;color:#eaf0f8;margin:0;padding:32px;max-width:1200px;margin:auto}
h1{font-size:36px}p{line-height:1.6;color:#bdccdf}.badge{color:#f3bc56;font-weight:bold}
.cards{display:flex;gap:16px;flex-wrap:wrap}article{background:#1b2d44;padding:24px;flex:1;min-width:160px;border-radius:12px}
strong{display:block;font-size:40px}svg{width:100%;background:#15253a;border-radius:12px}table{width:100%;border-collapse:collapse}
td,th{text-align:left;padding:12px;border-bottom:1px solid #34465b}select{padding:10px;margin:12px;background:#eaf0f8}
.scroll{overflow:auto;max-height:550px}a{color:#53ceb2}</style>
<span class="badge">SIMULATED DATA · OFFLINE LAB</span><h1>Feeder response analytics</h1>
<p>Python + SQLite · Feeder01 · 100 synthetic close requests. This report does not represent measured PLC or equipment performance.</p>
<div class="cards">CARDS</div><h2>Close request to position feedback</h2>
<p>Illustrative slow threshold: &gt;500 ms. Feedback deadline: 2,000 ms. Green = normal; amber = slow.
Blank bars mean no valid response measurement. These are lab thresholds, not equipment acceptance limits.</p>
<svg viewBox="0 0 980 260" role="img" aria-label="Close response times for 100 synthetic operations">
<text x="10" y="20" fill="white">ms</text><text x="5" y="124" fill="white">500</text>
<line x1="45" x2="950" y1="120" y2="120" stroke="#f3bc56" stroke-dasharray="5 5"/>
BARS<text x="45" y="247" fill="white">Close 1</text><text x="870" y="247" fill="white">Close 100</text></svg>
<h2>Operation history</h2><label>Show <select id="filter"><option value="ALL">All outcomes</option>
<option>NORMAL</option><option>SLOW</option><option>NO_FEEDBACK</option><option>UNKNOWN_DATA</option></select></label>
<div class="scroll"><table><thead><tr><th>Command time (UTC)</th><th>Feeder</th><th>Request</th><th>Outcome</th><th>Response (ms)</th></tr></thead>
<tbody>ROWS</tbody></table></div><p>NO_FEEDBACK means no target feedback observed by the deadline; it does not diagnose a mechanical fault.
UNKNOWN_DATA means quality or sampling continuity was lost. Timing includes acquisition resolution (100 ms here).
The PLC currently has one open-position bit, so a false bit is not independent proof of fully closed contacts.</p>
<p><a href="report.json">Download analysis JSON</a></p>
<script>document.querySelector('#filter').addEventListener('change',e=>{document.querySelectorAll('tbody tr').forEach(r=>r.hidden=e.target.value!=='ALL'&&r.cells[3].textContent!==e.target.value)})</script></html>'''
    (directory / 'report.html').write_text(page.replace('CARDS', cards).replace('BARS', bars).replace('ROWS', rows), encoding='utf-8')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['demo'])
    parser.add_argument('--output', type=Path, default=ROOT / 'output')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with connect(args.output / 'feeder.sqlite3') as db:
        run = simulate(db)
        analyze(db, run)
        data = report(db, run, args.output)
    print(json.dumps(dict(run_id=run, source='SIMULATED', summary=data['summary'],
                          report=str((args.output / 'report.html').resolve())), indent=2))


if __name__ == '__main__':
    main()
