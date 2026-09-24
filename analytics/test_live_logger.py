import json
from pathlib import Path
import tempfile
import unittest
from live_logger import connect, ingest

class LiveLoggerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = connect(self.root / 'test.sqlite3')
        self.file = self.root / 'snapshots-2026-09-23.jsonl'

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def row(self, time=1000, value=False, good=True):
        return json.dumps(dict(schema=1, source='LIVE', observed_ms=time,
          missed_events=False, tags=[dict(path='test', value=value,
            good=good, quality='Good' if good else 'Bad', timestamp_ms=time)]))

    def test_restart_does_not_duplicate(self):
        self.file.write_text(self.row() + '\n')
        self.assertEqual(ingest(self.db,self.root),1)
        self.assertEqual(ingest(self.db,self.root),0)
        self.assertEqual(self.db.execute('select count(*) from events').fetchone()[0],1)

    def test_partial_line_retried(self):
        self.file.write_text(self.row())
        self.assertEqual(ingest(self.db,self.root),0)
        with self.file.open('a') as f: f.write('\n')
        self.assertEqual(ingest(self.db,self.root),1)

    def test_quality_transition_and_gap_preserved(self):
        self.file.write_text(self.row()+'\n'+self.row(6000,good=False)+'\n')
        ingest(self.db,self.root)
        self.assertEqual(self.db.execute('select gap_ms from snapshots order by id desc').fetchone()[0],5000)
        self.assertEqual(self.db.execute('select count(*) from events').fetchone()[0],2)
        self.assertEqual(self.db.execute('select good from readings order by snapshot_id desc').fetchone()[0],0)

    def test_invalid_line_quarantined(self):
        self.file.write_text('{bad}\n'+self.row()+'\n')
        self.assertEqual(ingest(self.db,self.root),1)
        self.assertEqual(self.db.execute('select count(*) from rejects').fetchone()[0],1)

    def test_initial_high_is_initial_not_change(self):
        self.file.write_text(self.row(value=True)+'\n')
        ingest(self.db,self.root)
        self.assertEqual(self.db.execute('select kind from events').fetchone()[0],'INITIAL')

if __name__ == '__main__': unittest.main()
