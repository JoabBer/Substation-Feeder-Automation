"""Generate additive Perspective command panel for the software PLC lab."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
script = ''.join('    ' + line if line.strip() else line for line in
                 (ROOT / 'command_action.py').read_text().splitlines(keepends=True))

def label(name, text, y, height=34):
    return dict(type='ia.display.label', version=0, meta={'name': name},
                props={'text': text, 'style': {'fontSize': 15}},
                position={'x': 12, 'y': y, 'width': 650, 'height': height})

children = [label('Heading', 'LAB BREAKER CONTROLS', 8)]
for action, x in [('Open', 12), ('Close', 232)]:
    children.append(dict(type='ia.input.button', version=0, meta={'name': action+'Button'},
        custom={'command': action}, props={'text': 'Request '+action.upper()},
        position={'x': x, 'y': 48, 'width': 200, 'height': 44},
        events={'component': {'onActionPerformed': {'type': 'script', 'scope': 'G',
                                                    'config': {'script': script}}}}))
result = label('Result', 'Ready. Sign in to issue commands.', 104, 50)
result['propConfig'] = {'props.text': {'binding': {'type': 'property',
                            'config': {'path': 'parent.custom.result'}}}}
children += [result, label('Scope', 'Simulation only. Requests expire; feedback is manually simulated.', 162, 40)]
panel = dict(type='ia.container.coord', version=0, meta={'name': 'BreakerControls'},
    props={'style': {'backgroundColor': '#e2e8f0', 'borderRadius': 6}},
    custom={'result': 'Ready. Sign in to issue commands.'},
    position={'x':16, 'y':790, 'width':680, 'height':220}, children=children)
(ROOT/'Controls.components.json').write_text(json.dumps([panel], indent=2))
print('Generated Controls.components.json')
