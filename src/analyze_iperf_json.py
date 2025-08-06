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
        
def analyze_worst_case_by_second(self):
    """Analyze worst-case transfer times grouped by start second"""
    if not self.transfer_time_records:
        print("\nNo transfer time records with timestamps available for batch analysis")
        return
        
    # Sort records by start time
    sorted_records = sorted(self.transfer_time_records, key=lambda x: x['start_time'])
    
    # Find the range of timestamps
    min_time = sorted_records[0]['start_time']
    max_time = sorted_records[-1]['start_time']
    
    # Group by second and find worst case
    worst_case_by_second = {}
    for record in sorted_records:
        # Calculate which second this belongs to (relative to first connection)
        second_bucket = int(record['start_time'] - min_time)
        
        if second_bucket not in worst_case_by_second:
            worst_case_by_second[second_bucket] = record['duration']
        else:
            worst_case_by_second[second_bucket] = max(worst_case_by_second[second_bucket], 
                                                        record['duration'])
    
    # Convert to sorted list
    seconds = sorted(worst_case_by_second.keys())
    worst_case_times = [worst_case_by_second[s] for s in seconds]
    
    print(f"\n=== Worst-Case Transfer Time by Second ===")
    print(f"Total seconds with connections: {len(seconds)}")
    print(f"\nFirst 10 seconds: {[f'{t:.2f}s' for t in worst_case_times[:10]]}")
    
    # Create plot
    plt.figure(figsize=(12, 6))
    plt.plot(seconds, worst_case_times, 'b-', linewidth=2, marker='o', markersize=4)
    plt.xlabel('Time (seconds from first connection)')
    plt.ylabel('Worst-case Transfer Time (seconds)')
    plt.title('Worst-case Transfer Time by Second')
    plt.grid(True, alpha=0.3)
    
    # Add statistics as text
    avg_worst = np.mean(worst_case_times)
    max_worst = max(worst_case_times)
    min_worst = min(worst_case_times)
    plt.text(0.02, 0.98, f'Max: {max_worst:.2f}s\nAvg: {avg_worst:.2f}s\nMin: {min_worst:.2f}s', 
            transform=plt.gca().transAxes, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    output_path = os.path.join(self.output_dir, 'worst_case_transfer_time_by_second.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\nWorst-case plot saved: {output_path}")
    
    # Also print summary statistics
    print(f"\nSummary Statistics:")
    print(f"  Min worst-case: {min_worst:.2f}s")
    print(f"  Max worst-case: {max_worst:.2f}s") 
    print(f"  Avg worst-case: {avg_worst:.2f}s")
    print(f"  Std deviation: {np.std(worst_case_times):.2f}s")#!/usr/bin/env python3
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

class IperfJsonAnalyzer:
    def __init__(self, json_pattern, output_dir=None):
        self.json_pattern = json_pattern
        self.output_dir = output_dir or "iperf_analysis_results"
        self.data = {
            'transfer_times': [],
            'rtts': [],
            'throughputs': [],
            'receiver_throughputs': []
        }
        # New: store transfer times with start timestamps
        self.transfer_time_records = []
        # New: store transfer times with start timestamps
        self.transfer_time_records = []
        
    def setup_output_directory(self):
        """Create output directory for results"""
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"Output directory: {self.output_dir}")
        
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
                
            # Extract start timestamp
            start_timestamp = None
            if 'start' in data and 'timestamp' in data['start']:
                start_timestamp = data['start']['timestamp'].get('timesecs', 0)
                
            # Extract transfer time
            if 'end' in data:
                end_data = data['end']
                
                # Transfer time from receiver perspective
                if 'sum_received' in end_data:
                    duration = end_data['sum_received'].get('seconds', 0)
                    if duration > 0:
                        self.data['transfer_times'].append(duration)
                        
                        # Store with timestamp for batch analysis
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
        print("  Percentiles:")
        for p in [10, 25, 50, 75, 90, 95, 99]:
            value = np.percentile(data, p)
            print(f"    P{p}: {value:.2f} {unit}")
            
    def analyze_worst_case_by_second(self):
        """Analyze worst-case transfer times grouped by start second"""
        if not self.transfer_time_records:
            print("\nNo transfer time records with timestamps available for batch analysis")
            return
            
        # Sort records by start time
        sorted_records = sorted(self.transfer_time_records, key=lambda x: x['start_time'])
        
        # Find the range of timestamps
        min_time = sorted_records[0]['start_time']
        max_time = sorted_records[-1]['start_time']
        
        # Group by second and find worst case
        worst_case_by_second = {}
        for record in sorted_records:
            # Calculate which second this belongs to (relative to first connection)
            second_bucket = int(record['start_time'] - min_time)
            
            if second_bucket not in worst_case_by_second:
                worst_case_by_second[second_bucket] = record['duration']
            else:
                worst_case_by_second[second_bucket] = max(worst_case_by_second[second_bucket], 
                                                          record['duration'])
        
        # Convert to sorted list
        seconds = sorted(worst_case_by_second.keys())
        worst_case_times = [worst_case_by_second[s] for s in seconds]
        
        print(f"\n=== Worst-Case Transfer Time by Second ===")
        print(f"Total seconds with connections: {len(seconds)}")
        print(f"\nFirst 10 seconds: {[f'{t:.2f}s' for t in worst_case_times[:10]]}")
        
        # Create plot
        plt.figure(figsize=(12, 6))
        plt.plot(seconds, worst_case_times, 'b-', linewidth=2, marker='o', markersize=4)
        plt.xlabel('Time (seconds from first connection)')
        plt.ylabel('Worst-case Transfer Time (seconds)')
        plt.title('Worst-case Transfer Time by Second')
        plt.grid(True, alpha=0.3)
        
        # Add statistics as text
        avg_worst = np.mean(worst_case_times)
        max_worst = max(worst_case_times)
        min_worst = min(worst_case_times)
        plt.text(0.02, 0.98, f'Max: {max_worst:.2f}s\nAvg: {avg_worst:.2f}s\nMin: {min_worst:.2f}s', 
                transform=plt.gca().transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        output_path = os.path.join(self.output_dir, 'worst_case_transfer_time_by_second.png')
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\nWorst-case plot saved: {output_path}")
        
        # Also print summary statistics
        print(f"\nSummary Statistics:")
        print(f"  Min worst-case: {min_worst:.2f}s")
        print(f"  Max worst-case: {max_worst:.2f}s") 
        print(f"  Avg worst-case: {avg_worst:.2f}s")
        print(f"  Std deviation: {np.std(worst_case_times):.2f}s")
        
    def analyze(self):
        """Run the complete analysis"""
        print("=== iPerf3 JSON Analysis ===")
        
        # Setup
        self.setup_output_directory()
        
        # Load files
        json_files = self.load_json_files()
        
        # Extract metrics from each file
        print("\nExtracting metrics...")
        for json_file in json_files:
            self.extract_metrics_from_file(json_file)
            
        print(f"Extraction complete: {len(json_files)} files processed")
        
        # Generate individual CDFs
        print("\nGenerating CDFs...")
        
        if self.data['transfer_times']:
            self.generate_cdf(self.data['transfer_times'], 
                            'Transfer Time CDF', 'Time (seconds)', 
                            'transfer_time_cdf.png')
            self.print_statistics(self.data['transfer_times'], 'Transfer Time', 'seconds')
            
        if self.data['rtts']:
            self.generate_cdf(self.data['rtts'], 
                            'RTT CDF', 'RTT (milliseconds)', 
                            'rtt_cdf.png')
            self.print_statistics(self.data['rtts'], 'RTT', 'ms')
            
        if self.data['throughputs']:
            self.generate_cdf(self.data['throughputs'], 
                            'Interval Throughput CDF', 'Throughput (Gbps)', 
                            'throughput_cdf.png')
            self.print_statistics(self.data['throughputs'], 'Interval Throughput', 'Gbps')
            
        if self.data['receiver_throughputs']:
            self.generate_cdf(self.data['receiver_throughputs'], 
                            'Average Receiver Throughput CDF', 'Throughput (Gbps)', 
                            'receiver_throughput_cdf.png')
            self.print_statistics(self.data['receiver_throughputs'], 'Receiver Throughput', 'Gbps')
            
        # Generate combined report
        self.generate_combined_report()
        
        # Analyze worst-case transfer times by second
        self.analyze_worst_case_by_second()
        
        print(f"\n=== Analysis Complete ===")
        print(f"Results saved in: {self.output_dir}/")

@click.command()
@click.argument('json_pattern')
@click.option('--output-dir', '-o', help='Output directory for results')
@click.option('--server-side', is_flag=True, help='Analyze server-side logs (default is client-side)')
def main(json_pattern, output_dir, server_side):
    """
    Analyze iperf3 JSON logs and generate CDFs for various metrics
    
    JSON_PATTERN: Glob pattern for JSON files (e.g., "logs/*.json")
    
    Examples:
        ./analyze_iperf_json.py "experiment_*/iperf_logs/*.json"
        ./analyze_iperf_json.py "server_*.json" -o results/
        ./analyze_iperf_json.py "iperf_logs/*.json" --server-side
    """
    
    # Create analyzer
    analyzer = IperfJsonAnalyzer(json_pattern, output_dir)
    
    # Run analysis
    try:
        analyzer.analyze()
    except Exception as e:
        print(f"Analysis failed: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    main()