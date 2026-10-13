"""Session history and explicit local export."""
from collections import deque
import csv
import json
from pathlib import Path

MAX_SAMPLES = 3600


class Recorder:
    def __init__(self):
        self.samples = deque(maxlen=MAX_SAMPLES)
        self.enabled = False

    def add(self, sample):
        if self.enabled:
            self.samples.append(dict(sample))

    def save(self, filename):
        path = Path(filename)
        if path.suffix.lower() not in ('.json', '.csv'):
            raise ValueError('Export must be a .json or .csv file')
        rows = list(self.samples)
        if path.suffix.lower() == '.json':
            path.write_text(json.dumps(rows, indent=2), encoding='utf-8')
        else:
            with path.open('w', encoding='utf-8', newline='') as file:
                if rows:
                    writer = csv.DictWriter(file, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
        return len(rows)
