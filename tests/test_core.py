import csv
import json
import tempfile
import unittest
from pathlib import Path
from trace_monitor.collector import format_size, metric_snapshot, top_processes
from trace_monitor.recording import Recorder, MAX_SAMPLES


class TraceTests(unittest.TestCase):
    def test_size_format(self):
        self.assertEqual(format_size(1024), '1.0 KB')

    def test_metrics(self):
        data, disk, net = metric_snapshot()
        self.assertIn('cpu_percent', data)
        self.assertIn('memory_percent', data)
        self.assertGreaterEqual(data['network_recv_bytes_sec'], 0)

    def test_process_rows(self):
        self.assertLessEqual(len(top_processes(limit=3)), 3)

    def test_exports(self):
        r = Recorder()
        r.enabled = True
        r.add({'timestamp': '2026-10-13', 'cpu_percent': 22})
        with tempfile.TemporaryDirectory() as folder:
            csv_file = Path(folder) / 'data.csv'
            json_file = Path(folder) / 'data.json'
            self.assertEqual(r.save(csv_file), 1)
            self.assertEqual(r.save(json_file), 1)
            with csv_file.open(newline='') as handle:
                self.assertEqual(list(csv.DictReader(handle))[0]['cpu_percent'], '22')
            self.assertEqual(json.loads(json_file.read_text())[0]['cpu_percent'], 22)

    def test_history_bounded(self):
        r = Recorder()
        r.enabled = True
        for i in range(MAX_SAMPLES + 20):
            r.add({'n': i})
        self.assertEqual(len(r.samples), MAX_SAMPLES)


if __name__ == '__main__':
    unittest.main()
