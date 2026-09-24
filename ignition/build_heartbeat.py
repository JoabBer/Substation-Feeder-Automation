"""Build an additive Ignition import from the heartbeat's browsed OPC path."""
import argparse
import json
from pathlib import Path

VALUE_CHANGED = '''def valueChanged(tag, tagPath, previousValue, currentValue, initialChange, missedEvents):
    target = "[default]FeederDiagnostics/LastChangeMs"
    if initialChange or not currentValue.quality.isGood() or not previousValue.quality.isGood():
        system.tag.writeBlocking([target], [0])
    elif currentValue.value != previousValue.value:
        system.tag.writeBlocking([target], [system.date.toMillis(system.date.now())])
'''

QUALITY_CHANGED = '''def qualityChanged(tag, tagPath, previousValue, currentValue, initialChange, missedEvents):
    system.tag.writeBlocking(["[default]FeederDiagnostics/LastChangeMs"], [0])
'''

STATE_EXPRESSION = '''forceQuality(if(!isGood({[.]Counter}), "UNAVAILABLE",
if(!isGood({[.]LastChangeMs}) || {[.]LastChangeMs} <= 0, "WAITING",
if(toMillis(now(1000)) - {[.]LastChangeMs} < 0 || toMillis(now(1000)) - {[.]LastChangeMs} > 5000,
"STALE", "ACTIVE"))))'''


def build(opc_path):
    if not opc_path or 'Heartbeat.Counter' not in opc_path or 'TODO' in opc_path:
        raise ValueError('Supply the actual browsed Heartbeat.Counter OPC item path.')
    return {'tags': [{'name': 'FeederDiagnostics', 'tagType': 'Folder', 'tags': [
        {'name': 'LastChangeMs', 'tagType': 'AtomicTag', 'valueSource': 'memory',
         'dataType': 'Int8', 'value': 0,
         'documentation': 'Gateway-only heartbeat receipt time; zero requires a fresh good-to-good counter change.'},
        {'name': 'Counter', 'tagType': 'AtomicTag', 'valueSource': 'opc',
         'dataType': 'Int8', 'opcServer': 'CODESYS_Local', 'opcItemPath': opc_path,
         'readOnly': True, 'eventScripts': [
             {'eventid': 'valueChanged', 'script': VALUE_CHANGED.split('\n', 1)[1]},
             {'eventid': 'qualityChanged', 'script': QUALITY_CHANGED.split('\n', 1)[1]}]},
        {'name': 'State', 'tagType': 'AtomicTag', 'valueSource': 'expr',
         'dataType': 'String', 'expression': STATE_EXPRESSION,
         'documentation': 'ACTIVE means a changing PLC-task counter observed within 5 s; not a safety permissive.'}
    ]}]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opc-path', required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('FeederDiagnostics.tags.json'))
    args = parser.parse_args()
    args.output.write_text(json.dumps(build(args.opc_path), indent=2) + '\n', encoding='utf-8')
    print(args.output)
