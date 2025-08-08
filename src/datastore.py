#!/usr/bin/env python3
"""
Simple CSV datastore for experiment results
"""
import os
import pandas as pd
from datetime import datetime

class ExperimentDatastore:
    def __init__(self, csv_file="experiment_results.csv"):
        self.csv_file = csv_file
        self.headers = [
            'id', 'timestamp',
            'interface', 'speed', 'duration', 'Parallel.', 'Concur.', 'Freq', 'size',
            'offered load', 'Observed utilization', 'Total transfer time', 'tx', 'propagation',
            'rx_avg', 'rx_median', 'rx_max', 'transfer_avg', 'transfer_max'
        ]
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.csv_file):
            df = pd.DataFrame(columns=self.headers)
            df.to_csv(self.csv_file, index=False)
    
    def save_experiment(self, experiment_id, timestamp=None, **kwargs):
        """Save experiment results to CSV, updating existing row if ID exists"""
        # Load existing data
        try:
            df = pd.read_csv(self.csv_file)
        except (FileNotFoundError, pd.errors.EmptyDataError):
            df = pd.DataFrame(columns=self.headers)
        
        # Prepare new row data
        row_data = {header: kwargs.get(header, '') for header in self.headers}
        row_data['id'] = experiment_id
        row_data['timestamp'] = timestamp or datetime.now().isoformat()
        
        # Check if experiment_id already exists
        if experiment_id in df['id'].values:
            # Update existing row
            idx = df[df['id'] == experiment_id].index[0]
            for key, value in row_data.items():
                if value != '':  # Only update non-empty values
                    df.at[idx, key] = value
            print(f"Updated experiment {experiment_id} in {self.csv_file}")
        else:
            # Add new row
            new_row = pd.DataFrame([row_data])
            df = pd.concat([df, new_row], ignore_index=True)
            print(f"Added experiment {experiment_id} to {self.csv_file}")
        
        # Save back to CSV
        df.to_csv(self.csv_file, index=False)

# Global datastore instance
datastore = ExperimentDatastore()