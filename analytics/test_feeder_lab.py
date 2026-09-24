import unittest
from collections import Counter
import feeder_lab as lab


def sample(t, close=0, opened=1, quality='GOOD', op=0):
    return dict(timestamp_ms=t, cmd_close=close, cmd_open=op, cb_open=opened, quality=quality)


class AnalysisTests(unittest.TestCase):
    def test_seeded_scenarios(self):
        with lab.connect(':memory:') as db:
            run = lab.simulate(db)
            lab.analyze(db, run)
            closes = db.execute("SELECT * FROM operations WHERE direction='CLOSE' ORDER BY command_ms").fetchall()
            self.assertEqual(len(closes), 100)
            self.assertEqual(Counter(r['outcome'] for r in closes),
                             dict(NORMAL=91, SLOW=5, NO_FEEDBACK=2, UNKNOWN_DATA=2))
            self.assertEqual([i+1 for i, r in enumerate(closes) if r['outcome'] == 'SLOW'], [12,29,47,68,91])
            self.assertEqual([i+1 for i, r in enumerate(closes) if r['outcome'] == 'NO_FEEDBACK'], [35,80])
            self.assertEqual([i+1 for i, r in enumerate(closes) if r['outcome'] == 'UNKNOWN_DATA'], [55,95])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM operations WHERE direction='OPEN' AND outcome='NORMAL'").fetchone()[0], 98)
            lab.analyze(db, run)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM operations').fetchone()[0], 198)

    def test_threshold_boundary(self):
        for delay, expected in [(500, 'NORMAL'), (600, 'SLOW'), (2000, 'SLOW')]:
            rows = [sample(0)] + [sample(t, close=1, opened=int(t < 100+delay))
                                   for t in range(100, 100+delay+1, 100)]
            result = lab.classify(rows)
            self.assertEqual(result[0]['outcome'], expected)
            self.assertEqual(result[0]['response_ms'], delay)

    def test_no_cross_pairing(self):
        rows = [sample(0), sample(100, close=1), sample(200),
                sample(300, close=1), sample(400, close=1, opened=0)]
        result = lab.classify(rows)
        self.assertEqual([r['outcome'] for r in result], ['SUPERSEDED', 'NORMAL'])
        self.assertEqual(result[1]['response_ms'], 100)

    def test_gap_is_not_success(self):
        self.assertEqual(lab.classify([sample(0), sample(100, close=1), sample(400, opened=0)])[0]['outcome'], 'UNKNOWN_DATA')

    def test_bad_quality_is_not_success(self):
        self.assertEqual(lab.classify([sample(0), sample(100, close=1), sample(200, opened=0, quality='BAD')])[0]['outcome'], 'UNKNOWN_DATA')

    def test_initial_high_command_is_not_a_known_edge(self):
        self.assertEqual(lab.classify([sample(0, close=1)])[0]['outcome'], 'UNKNOWN_START')

    def test_truncated_window_is_not_failure(self):
        self.assertEqual(lab.classify([sample(0), sample(100, close=1)])[0]['outcome'], 'INCOMPLETE')

    def test_already_closed(self):
        self.assertEqual(lab.classify([sample(0, opened=0), sample(100, close=1, opened=0)])[0]['outcome'], 'ALREADY_AT_TARGET')

    def test_conflicting_commands(self):
        result = lab.classify([sample(0), sample(100, close=1, op=1)])
        self.assertEqual([r['outcome'] for r in result], ['CONFLICTING_COMMANDS']*2)

    def test_late_feedback_does_not_rewrite_timeout(self):
        rows = [sample(0)] + [sample(t, close=1, opened=int(t < 2200)) for t in range(100, 2300, 100)]
        self.assertEqual(lab.classify(rows)[0]['outcome'], 'NO_FEEDBACK')

    def test_time_order_validation(self):
        with self.assertRaises(ValueError):
            lab.classify([sample(100), sample(100)])


if __name__ == '__main__':
    unittest.main()
