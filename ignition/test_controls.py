"""Exercise the shipped Jython event body with mocked Gateway services."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

class Quality:
    def __init__(self, good=True): self.good = good
    def isGood(self): return self.good
    def __str__(self): return 'Good' if self.good else 'Bad'

class ControlsTests(unittest.TestCase):
    def run_command(self, authenticated=True, direction='Close', values=None, write_good=True):
        lock = Mock()
        lock.tryLock.return_value = True
        globals_ = {}
        panel = types.SimpleNamespace(custom=types.SimpleNamespace(result=''))
        component = types.SimpleNamespace(parent=panel, custom=types.SimpleNamespace(command=direction),
            session=types.SimpleNamespace(props=types.SimpleNamespace(auth=types.SimpleNamespace(authenticated=authenticated))))
        system = Mock()
        system.util.getGlobals.return_value = globals_
        values = values or [False, False, True, True, True, True, 'ACTIVE']
        system.tag.readBlocking.return_value = [types.SimpleNamespace(value=v, quality=Quality()) for v in values]
        system.opc.writeValue.return_value = Quality(write_good)
        modules = {name: types.ModuleType(name) for name in
                   ['java', 'java.util', 'java.util.concurrent', 'java.util.concurrent.locks']}
        modules['java.util.concurrent.locks'].ReentrantLock = lambda: lock
        source = (Path(__file__).parent/'command_action.py').read_text()
        scope = {'system': system}
        exec('def action(self, event):\n' + '\n'.join('    '+line for line in source.splitlines()), scope)
        with patch.dict(sys.modules, modules), patch('time.sleep'):
            scope['action'](component, None)
        return system, lock, panel.custom.result

    def test_unauthenticated_never_writes(self):
        system, lock, message = self.run_command(authenticated=False)
        system.opc.writeValue.assert_not_called()
        self.assertIn('Sign in', message)

    def test_close_writes_then_clears(self):
        system, lock, message = self.run_command()
        self.assertEqual([c.args[-1] for c in system.opc.writeValue.call_args_list], [True, False])
        self.assertTrue(system.opc.writeValue.call_args.args[1].endswith('Cmd_CB_Close'))
        lock.unlock.assert_called_once()

    def test_stale_heartbeat_blocks(self):
        system, lock, _ = self.run_command(values=[False,False,True,True,True,True,'STALE'])
        system.opc.writeValue.assert_not_called()
        lock.unlock.assert_called_once()

    def test_close_permissive_blocks(self):
        system, _, _ = self.run_command(values=[False,False,True,True,True,False,'ACTIVE'])
        system.opc.writeValue.assert_not_called()

    def test_existing_request_blocks(self):
        system, _, _ = self.run_command(values=[True,False,True,True,True,True,'ACTIVE'])
        system.opc.writeValue.assert_not_called()

    def test_open_requires_not_already_open(self):
        system, _, _ = self.run_command(direction='Open')
        system.opc.writeValue.assert_not_called()
        system, _, _ = self.run_command(direction='Open',values=[False,False,True,True,False,False,'ACTIVE'])
        self.assertEqual([c.args[-1] for c in system.opc.writeValue.call_args_list], [True,False])

    def test_uncertain_write_still_attempts_cleanup(self):
        system, lock, message = self.run_command(write_good=False)
        self.assertEqual([c.args[-1] for c in system.opc.writeValue.call_args_list], [True,False])
        lock.unlock.assert_called_once()
        self.assertIn('reset not confirmed', message)

if __name__ == '__main__': unittest.main()
