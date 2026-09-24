import json
from pathlib import Path
import tempfile
import unittest
from live_logger import connect, ingest
from live_report import summarize, render

class LiveReportTests(unittest.TestCase):
    def test_counts_exclude_initial_high_and_preserve_gaps(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            rows=[]
            for timestamp,value in [(1000,True),(2000,False),(6000,True)]:
                rows.append(dict(schema=1,source='LIVE',observed_ms=timestamp,tags=[dict(
                    path='[default]Feeder01/Cmd_CB_Open',value=value,good=True,quality='Good',timestamp_ms=timestamp)]))
            (root/'snapshots-test.jsonl').write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
            db=connect(root/'test.sqlite3')
            ingest(db,root)
            result=summarize(db,10000)
            self.assertEqual(result['observed_rising_edges']['Cmd_CB_Open'],1)
            self.assertEqual(len(result['acquisition_gaps']),1)
            self.assertEqual(result['age_seconds'],4)
            self.assertIn('LIVE SQL DATA',render(result))
            db.close()

    def test_empty_database(self):
        with tempfile.TemporaryDirectory() as directory:
            db=connect(Path(directory)/'test.sqlite3')
            result=summarize(db,10000)
            self.assertEqual(result['snapshots'],0)
            self.assertIsNone(result['age_seconds'])
            render(result)
            db.close()

if __name__=='__main__': unittest.main()
