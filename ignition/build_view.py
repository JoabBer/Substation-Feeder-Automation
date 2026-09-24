"""Assemble the additive component packages into one portable HMI view."""
import json
from pathlib import Path
root = Path(__file__).resolve().parent
children = []
for filename in ['FeederOverview.components.json', 'Heartbeat.components.json',
                 'Alarm.components.json', 'Controls.components.json']:
    children.extend(json.loads((root/filename).read_text(encoding='utf-8-sig')))
children[0]['position']['y'] = 60
for child in children[0]['children']:
    text = child.get('props', {}).get('text', '')
    if 'READ ONLY' in text:
        child['props']['text'] = text.replace('READ ONLY', 'SUPERVISORY CONTROL')
for child in children:
    if child['meta']['name'] == 'BreakerControls':
        child['custom']['result'] = 'Ready. Commands require a signed-in session.'
view = {'custom':{}, 'params':{}, 'props':{'defaultSize':{'width':800,'height':1040}},
        'root':{'type':'ia.container.coord','version':0,'meta':{'name':'root'},
                'props':{'mode':'fixed'},'children':children}}
(root/'FeederOverview.view.json').write_text(json.dumps(view,indent=2),encoding='utf-8')
(root/'FeederOverview.all-components.json').write_text(json.dumps(children,indent=2),encoding='utf-8')
print('Generated complete view and combined component package')
