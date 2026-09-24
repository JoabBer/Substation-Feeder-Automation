"""Create a static portfolio graphic from live_report.json (not a UI screenshot)."""
import argparse
import json
from html import escape
from pathlib import Path
from datetime import datetime, timezone

def render(data):
    def date(ms):
        return 'No observations' if ms is None else datetime.fromtimestamp(ms/1000, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720" role="img" aria-labelledby="title desc">',
        '<title id="title">Live SQL analytics summary</title>',
        '<desc id="desc">Generated figure from recorded software PLC observations, not an application screenshot.</desc>',
        '<rect width="1200" height="720" fill="#102033"/>',
        '<g font-family="Arial, sans-serif" fill="#edf4ff">']
    def text(x,y,value,size=20,color='#edf4ff'):
        parts.append('<text x="%s" y="%s" font-size="%s" fill="%s">%s</text>' % (x,y,size,color,escape(str(value))))
    text(40,60,'LIVE SQL ANALYTICS',34)
    text(40,96,'Software PLC lab • Generated summary figure • Manually simulated feedback',19,'#a9c6e5')
    text(40,131,'Latest observation: '+date(data['latest_ms']),17)
    cards=[('Snapshots',data['snapshots']),('Close requests observed',data['observed_rising_edges']['Cmd_CB_Close']),
        ('Open requests observed',data['observed_rising_edges']['Cmd_CB_Open']),('Alarm activations observed',data['observed_alarm_activations'])]
    for index,(label,value) in enumerate(cards):
        x=40+index*285
        parts.append('<rect x="%s" y="166" width="265" height="120" rx="9" fill="#22364c"/>'%x)
        text(x+18,219,f'{value:,}',36)
        text(x+18,257,label,17)
    text(40,338,'Data quality and recording coverage',25)
    rows=[('Heartbeat sample counts',', '.join('%s: %s'%(k,v) for k,v in data['heartbeat_samples'].items())),
          ('Samples with bad quality',data['snapshots_with_bad_quality']),
          ('Recorded acquisition gaps',len(data['acquisition_gaps'])),('Rejected records',data['rejected_records'])]
    for i,(label,value) in enumerate(rows):
        y=384+i*40
        text(40,y,label,19,'#a9c6e5');text(420,y,value,19)
    text(40,579,'Counts represent observed transitions, not guaranteed operation totals.',19)
    text(40,610,'One-second sampling may miss short pulses; historical gaps are preserved.',19)
    text(40,641,'A false open indication does not confirm closed. No mechanical travel time is inferred.',19)
    text(40,688,'Generated: '+date(data['generated_ms'])+' • Source: Python report of LIVE SQLite records',15,'#a9c6e5')
    parts += ['</g></svg>']
    return '\n'.join(parts)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path(__file__).resolve().parent/'output/live-report.json')
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent.parent/'docs/images/live-sql-summary.svg')
    args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(render(json.loads(args.input.read_text(encoding='utf-8'))),encoding='utf-8')
    print(args.output)
