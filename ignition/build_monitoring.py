"""Additive lab alarm and read-only Gateway snapshot spool."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'analytics' / 'live'
OUT.mkdir(exist_ok=True)
names = list(json.loads((ROOT / 'ignition/node-map.json').read_text()))
paths = ['[default]Feeder01/' + name for name in names] + [
    '[default]FeederDiagnostics/State',
    '[default]FeederDiagnostics/Counter',
    '[default]FeederMonitoring/OpenPending',
    '[default]FeederMonitoring/OpenPending/Alarms/OpenFeedbackMissing.IsActive',
]
healthy = 'isGood({[default]Feeder01/Out_CB_Open}) && isGood({[default]Feeder01/Sts_CB_Open}) && isGood({[default]FeederDiagnostics/State}) && {[default]FeederDiagnostics/State} = "ACTIVE"'
script = '''    if not currentValue.quality.isGood():
        return
    try:
        paths = PATHS
        values = system.tag.readBlocking(paths)
        row = {"schema": 1, "source": "LIVE", "observed_ms": system.date.toMillis(system.date.now()), "missed_events": bool(missedEvents), "tags": []}
        for path, q in zip(paths, values):
            value = q.value
            if value is not None and not isinstance(value, (bool, int, long, float, basestring)):
                value = str(value)
            row["tags"].append({"path": path, "value": value, "quality": str(q.quality), "good": q.quality.isGood(), "timestamp_ms": system.date.toMillis(q.timestamp)})
        day = system.date.format(system.date.now(), "yyyy-MM-dd")
        system.file.writeFile(DIRECTORY + "/snapshots-" + day + ".jsonl", system.util.jsonEncode(row) + "\\n", True)
        system.tag.writeBlocking(["[default]FeederMonitoring/SpoolStatus"], ["OK"])
    except Exception as exc:
        system.tag.writeBlocking(["[default]FeederMonitoring/SpoolStatus"], ["ERROR: " + str(exc)])
        system.util.getLogger("FeederLiveSpool").error(str(exc))
'''.replace('PATHS', repr(paths)).replace('DIRECTORY', repr(OUT.as_posix()))
tags = [
    {'name': 'OpenPending', 'tagType': 'AtomicTag', 'valueSource': 'expr', 'dataType': 'Boolean',
     'expression': 'forceQuality(if(' + healthy + ', {[default]Feeder01/Out_CB_Open} && !{[default]Feeder01/Sts_CB_Open}, false))',
     'documentation': 'LAB ONLY: sustained open output without open indication. Clears on withdrawn output or unhealthy monitoring; false does not prove successful operation.',
     'alarms': [{'name': 'OpenFeedbackMissing', 'mode': 'WhenTrue', 'priority': 'High',
                 'timeOnDelaySeconds': 5.0, 'ackMode': 'Auto',
                 'label': 'Open output active without open feedback for 5 s',
                 'displayPath': 'Feeder01/Open feedback missing'}]},
    {'name': 'SpoolStatus', 'tagType': 'AtomicTag', 'valueSource': 'memory', 'dataType': 'String', 'value': 'STARTING'},
    {'name': 'SnapshotTick', 'tagType': 'AtomicTag', 'valueSource': 'expr', 'dataType': 'Int8',
     'expression': 'toMillis(now(1000))', 'eventScripts': [{'eventid': 'valueChanged', 'script': script}]},
]
(ROOT / 'ignition/FeederMonitoring.tags.json').write_text(json.dumps({'tags': [{'name': 'FeederMonitoring', 'tagType': 'Folder', 'tags': tags}]}, indent=2))
print('Generated FeederMonitoring.tags.json')
