#!/usr/bin/env python3
"""
Simple CSV datastore for experiment results
"""
import csv
import os
from datetime import datetime

class ExperimentDatastore:
    def __init__(self, csv_file="experiment_results.csv"):
        self.csv_file = csv_file
        self.headers = [
            'id', 'timestamp',
            'interface', 'speed', 'duration', 'Parallel.', 'Concur.', 'Freq', 'size',
            'offered load', 'Observed utilization', 'Total transfer time', 'tx', 'propagation',
            'rx_avg', 'rx_median', 'rx_max'
        ]
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(self.headers)
    
    def save_experiment(self, experiment_id, timestamp=None, **kwargs):
        """Save experiment results to CSV"""
        row = {header: kwargs.get(header, '') for header in self.headers}
        row['id'] = experiment_id
        row['timestamp'] = timestamp or datetime.now().isoformat()
        
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.headers)
            writer.writerow(row)
        
        print(f"Saved experiment {experiment_id} to {self.csv_file}")

# Global datastore instance
datastore = ExperimentDatastore()