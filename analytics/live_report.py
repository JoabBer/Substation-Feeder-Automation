"""Generate a read-only HTML/JSON report from the LIVE SQLite database."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import sqlite3
import time

ROOT = Path(__file__).resolve().parent

def summarize(db, now_ms):
    db.row_factory = sqlite3.Row
    first, last, count = db.execute('SELECT MIN(observed_ms),MAX(observed_ms),COUNT(*) FROM snapshots').fetchone()
    events = [dict(r) for r in db.execute('''SELECT s.observed_ms,e.path,e.previous_json,e.value_json,e.quality,e.kind
        FROM events e JOIN snapshots s ON s.id=e.snapshot_id
        WHERE e.path NOT LIKE '%/Counter' ORDER BY e.id DESC LIMIT 500''')]
    counts = {}
    for name in ['Cmd_CB_Open','Cmd_CB_Close','Out_CB_Open','Out_CB_Close']:
        counts[name] = db.execute('''SELECT COUNT(*) FROM events WHERE path=?
          AND kind='CHANGE' AND previous_json='false' AND value_json='true' AND quality='Good' ''',
          ('[default]Feeder01/'+name,)).fetchone()[0]
    alarms = db.execute("SELECT COUNT(*) FROM events WHERE path LIKE '%OpenFeedbackMissing.IsActive' AND kind='CHANGE' AND previous_json='false' AND value_json='true' AND quality='Good'").fetchone()[0]
    gaps = [dict(r) for r in db.execute('SELECT observed_ms,gap_ms FROM snapshots WHERE gap_ms>2500 OR gap_ms<=0 ORDER BY id DESC')]
    health = dict(db.execute('SELECT heartbeat,COUNT(*) FROM snapshots GROUP BY heartbeat').fetchall())
    bad = db.execute('SELECT COUNT(DISTINCT snapshot_id) FROM readings WHERE good=0').fetchone()[0]
    return dict(source='LIVE', generated_ms=now_ms, first_ms=first, latest_ms=last,
        age_seconds=None if last is None else round((now_ms-last)/1000,1),
        snapshots=count, observed_rising_edges=counts, observed_alarm_activations=alarms,
        heartbeat_samples=health, snapshots_with_bad_quality=bad, acquisition_gaps=gaps,
        rejected_records=db.execute('SELECT COUNT(*) FROM rejects').fetchone()[0], recent_events=events)

def utc(ms):
    return '—' if ms is None else datetime.fromtimestamp(ms/1000,timezone.utc).isoformat(timespec='seconds')

def render(data):
    esc=lambda value: html.escape(str(value))
    rows=''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in
        [utc(e['observed_ms']),e['path'].replace('[default]',''),e['value_json'],e['quality'],e['kind']])+'</tr>'
        for e in data['recent_events'])
    cards = [('Snapshots',data['snapshots']),('Open requests observed',data['observed_rising_edges']['Cmd_CB_Open']),
             ('Close requests observed',data['observed_rising_edges']['Cmd_CB_Close']),
             ('Alarm activations observed',data['observed_alarm_activations']),('Acquisition gaps',len(data['acquisition_gaps']))]
    return ('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Live feeder history</title><style>body{font:16px system-ui;max-width:1200px;margin:32px auto;padding:0 20px;background:#102033;color:#edf4ff}p{line-height:1.6}.cards{display:flex;flex-wrap:wrap;gap:12px}.card{background:#22364c;padding:20px;border-radius:8px}strong{display:block;font-size:30px}table{width:100%;border-collapse:collapse}td,th{padding:10px;text-align:left;border-bottom:1px solid #496078}.scroll{overflow:auto;max-height:600px}a{color:#92d8ff}</style>
<h1>Live feeder history</h1><p>LIVE SQL DATA · Software PLC · Manually simulated breaker feedback</p>'''+(
        '<p>Generated '+esc(utc(data['generated_ms']))+' · Latest observation '+esc(utc(data['latest_ms']))+
        ' · Age at generation: '+esc(data['age_seconds'])+' seconds.</p>')+
        '<div class="cards">'+''.join('<div class="card"><strong>'+esc(v)+'</strong>'+esc(k)+'</div>' for k,v in cards)+'</div>'+(
        '<p>Counts are observed transitions, not guaranteed operation totals. One-second sampling can miss short pulses. '
        'Initial high values are not counted as new requests. Bad-quality samples, stale heartbeat and gaps limit interpretation. '
        'A false open indication does not confirm CLOSED. This report does not calculate mechanical travel time.</p>')+
        '<p>Heartbeat sample counts: '+esc(data['heartbeat_samples'])+' · Samples with bad quality: '+esc(data['snapshots_with_bad_quality'])+'</p>'+(
        '<p>This is a generated snapshot; rerun the report to refresh. <a href="live-report.json">Download report data</a></p>'
        '<h2>Recent observed events (up to 500)</h2><div class="scroll"><table><thead><tr><th>UTC</th><th>Signal</th><th>Value</th><th>Quality</th><th>Event</th></tr></thead><tbody>')+rows+'</tbody></table></div></html>')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,default=ROOT/'live/feeder-live.sqlite3')
    parser.add_argument('--output',type=Path,default=ROOT/'output')
    args=parser.parse_args()
    with sqlite3.connect(args.database.resolve().as_uri()+'?mode=ro',uri=True) as db:
        db.execute('BEGIN')
        data=summarize(db,int(time.time()*1000))
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'live-report.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    (args.output/'live-report.html').write_text(render(data),encoding='utf-8')
    print(args.output/'live-report.html')

if __name__=='__main__': main()

