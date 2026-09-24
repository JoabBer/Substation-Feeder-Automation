"""Exercise the actual generated tag event scripts without a live Gateway."""
import unittest
from types import SimpleNamespace
from build_heartbeat import VALUE_CHANGED, QUALITY_CHANGED, build


class HeartbeatEvents(unittest.TestCase):
    def setUp(self):
        self.writes = []
        scope = {'system': SimpleNamespace(
            tag=SimpleNamespace(writeBlocking=lambda paths, values: self.writes.append((paths, values))),
            date=SimpleNamespace(now=lambda: 123456, toMillis=lambda value: value))}
        # Ignition supplies the function header; imported scripts contain
        # the indented body only. Exercise that exact serialization contract.
        counter = build('verified.Heartbeat.Counter')['tags'][0]['tags'][1]
        for event, source in zip(counter['eventScripts'], [VALUE_CHANGED, QUALITY_CHANGED]):
            exec(source.split('\n', 1)[0] + '\n' + event['script'], scope)
        self.value_changed = scope['valueChanged']
        self.quality_changed = scope['qualityChanged']

    def qv(self, value, good=True):
        return SimpleNamespace(value=value, quality=SimpleNamespace(isGood=lambda: good))

    def change(self, old, new, initial=False):
        self.value_changed(None, 'unused', old, new, initial, False)

    def test_first_observation_does_not_prove_running(self):
        self.change(self.qv(None, False), self.qv(10), True)
        self.assertEqual(self.writes[-1][1], [0])

    def test_good_change_updates_receipt_time(self):
        self.change(self.qv(10), self.qv(12))
        self.assertEqual(self.writes[-1][1], [123456])

    def test_frozen_counter_does_not_refresh(self):
        self.change(self.qv(10), self.qv(10))
        self.assertEqual(self.writes, [])

    def test_quality_recovery_requires_another_change(self):
        self.change(self.qv(10, False), self.qv(12))
        self.assertEqual(self.writes[-1][1], [0])

    def test_wrap_is_a_valid_change(self):
        self.change(self.qv(4294967295), self.qv(0))
        self.assertEqual(self.writes[-1][1], [123456])

    def test_quality_transition_resets_observation(self):
        self.quality_changed(None, 'unused', self.qv(10), self.qv(10, False), False, False)
        self.assertEqual(self.writes[-1][1], [0])


if __name__ == '__main__':
    unittest.main()
