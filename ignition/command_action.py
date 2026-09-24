# Perspective onActionPerformed body; build_controls.py indents this file.
# LAB ONLY. No physical breaker I/O is connected.
from java.util.concurrent.locks import ReentrantLock
import time

panel = self.parent
action = self.custom.command
if action not in ('Open', 'Close'):
    return
if not self.session.props.auth.authenticated:
    panel.custom.result = 'Sign in before issuing a command.'
    return

# Gateway-wide serialization, shared by both buttons and all sessions.
lock = system.util.getGlobals().setdefault('FeederLab.CommandLock', ReentrantLock())
if not lock.tryLock():
    panel.custom.result = 'Another command is active. Wait for it to finish.'
    return
server = 'CODESYS_Local'
prefix = 'nsu=CODESYSSPV3/3S/IecVarAccess;s=|var|CODESYS Control Win V3 x64.Application.PLC_PRG.'
node = prefix + 'Cmd_CB_' + action
started = False
try:
    names = ['Cmd_CB_Open', 'Cmd_CB_Close', 'Mode_Remote', 'Sts_DC_Healthy',
             'Sts_CB_Open', 'Perm_CB_Close']
    values = system.tag.readBlocking(['[default]Feeder01/' + n for n in names] +
                                    ['[default]FeederDiagnostics/State'])
    if not all(q.quality.isGood() for q in values) or str(values[-1].value) != 'ACTIVE':
        panel.custom.result = 'Command blocked: PLC monitoring unavailable.'
        return
    state = dict(zip(names, [bool(q.value) for q in values[:-1]]))
    if state['Cmd_CB_Open'] or state['Cmd_CB_Close']:
        panel.custom.result = 'Command blocked: an existing request is active.'
        return
    allowed = state['Perm_CB_Close'] if action == 'Close' else (
        state['Mode_Remote'] and state['Sts_DC_Healthy'] and not state['Sts_CB_Open'])
    if not allowed:
        panel.custom.result = action + ' blocked by PLC conditions.'
        return
    # Set before attempting the write so an uncertain write is still cleaned up.
    started = True
    quality = system.opc.writeValue(server, node, True)
    if not quality.isGood():
        raise Exception('PLC command write failed: ' + str(quality))
    panel.custom.result = action + ' requested. Waiting for indication; request clears within 6 s.'
    # This Gateway event continues if the browser disconnects. PLC has a 7 s cap.
    time.sleep(6.0)
    panel.custom.result = action + ' request ended. Check the breaker indication.'
except Exception as exc:
    panel.custom.result = 'Command error: ' + str(exc)
    system.util.getLogger('FeederLabCommands').error(str(exc))
finally:
    try:
        if started:
            quality = system.opc.writeValue(server, node, False)
            if not quality.isGood():
                panel.custom.result = 'Command reset not confirmed. PLC timeout is the fallback.'
    finally:
        lock.unlock()
