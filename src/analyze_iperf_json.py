#!/usr/bin/env python3
"""
Analyze iperf3 JSON logs to generate CDFs for various metrics
"""
import json
import numpy as np
import matplotlib.pyplot as plt
import click
import glob
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

class IperfJsonAnalyzer:
    def __init__(self, json_pattern, output_dir=None, experiment_id=None):
        self.json_pattern = json_pattern
        self.output_dir = output_dir or "iperf_analysis_results"
        self.experiment_id = experiment_id
        self.data = {
            'transfer_times': [],
            'rtts': [],
            'throughputs': [],
            'receiver_throughputs': []
        }
        self.transfer_time_records = []
        self.worst_case_per_second = {}
        
    def setup_output_directory(self):
        """Create output directory for results"""
        os.makedirs(self.output_dir, exist_ok=True)
        
    def load_json_files(self):
        """Load all JSON files matching the pattern"""
        self.json_files = glob.glob(self.json_pattern)
        if not self.json_files:
            raise ValueError(f"No files found matching pattern: {self.json_pattern}")
        print(f"Found {len(self.json_files)} JSON files to analyze")
        return self.json_files
        
    def extract_metrics_from_file(self, json_file):
        """Extract various metrics from a single iperf3 JSON file"""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                
            start_timestamp = None
            if 'start' in data and 'timestamp' in data['start']:
                start_timestamp = data['start']['timestamp']['timesecs']
                
            # Extract transfer time
            if 'end' in data:
                end_data = data['end']
                
                # Transfer time from receiver perspective
                if 'sum_received' in end_data:
                    duration = end_data['sum_received'].get('seconds', 0)
                    if duration > 0:
                        self.data['transfer_times'].append(duration)
                        
                        if start_timestamp:
                            self.transfer_time_records.append({
                                'start_time': start_timestamp,
                                'duration': duration
                            })
                        
                    # Average receiver throughput
                    avg_bps = end_data['sum_received'].get('bits_per_second', 0)
                    if avg_bps > 0:
                        self.data['receiver_throughputs'].append(avg_bps / 1e9)  # Convert to Gbps
                
                # Stream-specific metrics
                if 'streams' in end_data:
                    for stream in end_data['streams']:
                        # Sender metrics (if this is a client-side log)
                        if 'sender' in stream:
                            sender = stream['sender']
                            
                            # RTT (mean)
                            if 'mean_rtt' in sender:
                                rtt_us = sender['mean_rtt']
                                self.data['rtts'].append(rtt_us / 1000.0)  # Convert to ms
                        
                        # Receiver metrics
                        if 'receiver' in stream:
                            receiver = stream['receiver']
                            
                            # RTT from receiver side (if available)
                            if 'mean_rtt' in receiver:
                                rtt_us = receiver['mean_rtt']
                                self.data['rtts'].append(rtt_us / 1000.0)  # Convert to ms
            
            # Extract interval data for throughput distribution
            if 'intervals' in data:
                for interval in data['intervals']:
                    if 'sum' in interval:
                        interval_bps = interval['sum'].get('bits_per_second', 0)
                        if interval_bps > 0:
                            self.data['throughputs'].append(interval_bps / 1e9)  # Convert to Gbps
                                
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
    
    def batch_and_compute_worst_case(self):
        """Batch transfer times by 1-second intervals and find worst case per second"""
        if not self.transfer_time_records:
            print("No transfer time records with timestamps available for batching")
            return
        
        batches = defaultdict(list)
        for record in self.transfer_time_records:
            second_bucket = int(record['start_time'])
            batches[second_bucket].append(record['duration'])
        
        self.worst_case_per_second = {}
        for second, durations in sorted(batches.items()):
            self.worst_case_per_second[second] = max(durations)
        
        if self.worst_case_per_second:
            sorted_seconds = sorted(self.worst_case_per_second.keys())
            self.worst_case_array = [self.worst_case_per_second[s] for s in sorted_seconds]
            
            print("\nWorst-case transfer times per second (first 10):")
            first_10 = self.worst_case_array[:10]
            print("  " + " ".join([f"{val:.3f}" for val in first_10]))
            
            self.plot_worst_case_transfer_times()
    
    def plot_worst_case_transfer_times(self):
        """Plot the worst case transfer times per second"""
        if not hasattr(self, 'worst_case_array'):
            return
            
        plt.figure(figsize=(12, 6))
        
        # Time series plot
        plt.subplot(1, 2, 1)
        plt.plot(range(len(self.worst_case_array)), self.worst_case_array, 'b-', linewidth=1)
        plt.xlabel('Time (seconds from start)')
        plt.ylabel('Worst-case Transfer Time (seconds)')
        plt.title(f'Worst-case Transfer Time per Second (n={len(self.worst_case_array)})')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = os.path.join(self.output_dir, 'worst_case_transfer_times.png')
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Saved worst-case plot: worst_case_transfer_times.png")
          
    def generate_cdf(self, data, title, xlabel, filename, ax=None):
        """Generate and save a CDF plot"""
        if not data:
            print(f"No data available for {title}")
            return
            
        sorted_data = np.sort(data)
        cdf = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
        
        if ax is None:
            plt.figure(figsize=(10, 6))
            ax = plt.gca()
        
        ax.plot(sorted_data, cdf, linewidth=2)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel(xlabel)
        ax.set_ylabel('Cumulative Probability')
        ax.set_title(f'{title} (n={len(data)})')
        
        # Add percentile markers
        percentiles = [10, 25, 50, 75, 90, 95, 99]
        for p in percentiles:
            value = np.percentile(sorted_data, p)
            if p in [50, 90, 95, 99]:  # Only show lines for key percentiles
                ax.axhline(y=p/100, color='gray', linestyle='--', alpha=0.3)
                ax.text(sorted_data.max() * 1.02, p/100, f'P{p}', 
                       verticalalignment='center', fontsize=8)
        
        ax.set_ylim(0, 1)
        ax.set_xlim(0, sorted_data.max() * 1.05)
        
        if ax == plt.gca():
            output_path = os.path.join(self.output_dir, filename)
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
            print(f"  Saved: {filename}")
            
        # Return percentile summary
        percentile_summary = {}
        for p in percentiles:
            percentile_summary[f'P{p}'] = np.percentile(sorted_data, p)
        return percentile_summary
        
    def print_statistics(self, data, name, unit):
        """Print summary statistics for a metric"""
        if not data:
            return
            
        print(f"\n{name} Statistics:")
        print(f"  Samples: {len(data)}")
        print(f"  Min: {min(data):.2f} {unit}")
        print(f"  Max: {max(data):.2f} {unit}")
        print(f"  Mean: {np.mean(data):.2f} {unit}")
        print(f"  Median: {np.median(data):.2f} {unit}")
        print(f"  Std Dev: {np.std(data):.2f} {unit}")
        
        # Percentiles
        #print("  Percentiles:")
        #for p in [10, 25, 50, 75, 90, 95, 99]:
        #    value = np.percentile(data, p)
        #    print(f"    P{p}: {value:.2f} {unit}")
            
    def generate_combined_report(self):
        """Generate a combined report with multiple CDFs on one page"""
        # Count how many metrics we have data for
        available_metrics = sum(1 for metric in self.data.values() if metric)
        
        if available_metrics == 0:
            print("No data available for plotting")
            return
            
        # Calculate grid size
        cols = 2
        rows = (available_metrics + 1) // 2
        
        fig, axes = plt.subplots(rows, cols, figsize=(15, 5*rows))
        if rows == 1:
            axes = axes.reshape(1, -1)
        
        plot_idx = 0
        
        # Plot each metric
        metric_configs = [
            ('transfer_times', 'Transfer Time CDF', 'Time (seconds)'),
            ('rtts', 'RTT CDF', 'RTT (milliseconds)'),
            ('throughputs', 'Interval Throughput CDF', 'Throughput (Gbps)'),
            ('receiver_throughputs', 'Average Receiver Throughput CDF', 'Throughput (Gbps)'),
        ]
        
        for metric_key, title, xlabel in metric_configs:
            if self.data[metric_key]:
                row = plot_idx // cols
                col = plot_idx % cols
                ax = axes[row, col] if available_metrics > 1 else axes
                
                self.generate_cdf(self.data[metric_key], title, xlabel, 
                                 f"{metric_key}_cdf.png", ax=ax)
                plot_idx += 1
        
        # Hide empty subplots
        while plot_idx < rows * cols:
            row = plot_idx // cols
            col = plot_idx % cols
            axes[row, col].set_visible(False)
            plot_idx += 1
        
        plt.tight_layout()
        combined_path = os.path.join(self.output_dir, 'combined_cdfs.png')
        plt.savefig(combined_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\nCombined report saved: {combined_path}")
        
    def analyze(self):
        """Run the complete analysis"""
        print("=== iPerf3 JSON Analysis ===")
        
        # Setup
        self.setup_output_directory()
        
        # Load files
        json_files = self.load_json_files()
        
        for json_file in json_files:
            self.extract_metrics_from_file(json_file)
            
        print(f"Extraction complete: {len(json_files)} files processed")
        
        # New: Batch and compute worst-case analysis
        self.batch_and_compute_worst_case()
        
        if self.data['transfer_times']:
            self.generate_cdf(self.data['transfer_times'], 
                            'Transfer Time CDF', 'Time (seconds)', 
                            'transfer_time_cdf.png')
            self.print_statistics(self.data['transfer_times'], 'Transfer Time', 'seconds')
            
            # Save to datastore if experiment_id provided
            if self.experiment_id:
                try:
                    from datastore import datastore
                    transfer_avg = np.mean(self.data['transfer_times'])
                    transfer_max = max(self.data['transfer_times'])
                    datastore.save_experiment(self.experiment_id, **{
                        'transfer_avg': transfer_avg,
                        'transfer_max': transfer_max})
                except ImportError:
                    pass
            
        if self.data['rtts']:
            self.generate_cdf(self.data['rtts'], 
                            'RTT CDF', 'RTT (milliseconds)', 
                            'rtt_cdf.png')
            self.print_statistics(self.data['rtts'], 'RTT', 'ms')
            
        if self.data['throughputs']:
            self.generate_cdf(self.data['throughputs'], 
                            'Interval Throughput CDF', 'Throughput (Gbps)', 
                            'throughput_cdf.png')
            #self.print_statistics(self.data['throughputs'], 'Interval Throughput', 'Gbps')
            
        if self.data['receiver_throughputs']:
            self.generate_cdf(self.data['receiver_throughputs'], 
                            'Average Receiver Throughput CDF', 'Throughput (Gbps)', 
                            'receiver_throughput_cdf.png')
            #self.print_statistics(self.data['receiver_throughputs'], 'Receiver Throughput', 'Gbps')
            
        # Generate combined report
        self.generate_combined_report()
        
        print(f"\n=== Analysis Complete ===")
        print(f"Results saved in: {self.output_dir}")

@click.command()
@click.argument('json_pattern')
@click.option('--output-dir', '-o', help='Output directory for results')
@click.option('--server-side', is_flag=True, help='Analyze server-side logs (default is client-side)')
@click.option('--experiment-id', help='Experiment ID for datastore')
def main(json_pattern, output_dir, server_side, experiment_id):
    """
    Analyze iperf3 JSON logs and generate CDFs for various metrics
    
    JSON_PATTERN: Glob pattern for JSON files (e.g., "logs/*.json")
    
    Examples:
        ./analyze_iperf_json.py "experiment_*/iperf_logs/*.json"
        ./analyze_iperf_json.py "server_*.json" -o results/
        ./analyze_iperf_json.py "iperf_logs/*.json" --server-side
    """
    
    # Create analyzer
    analyzer = IperfJsonAnalyzer(json_pattern, output_dir, experiment_id)
    
    # Run analysis
    try:
        analyzer.analyze()
    except Exception as e:
        print(f"Analysis failed: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    main()
