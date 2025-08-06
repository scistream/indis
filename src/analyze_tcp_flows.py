#!/usr/bin/env python3
"""
Analyze TCP flow data from tcp_flow_monitor.py with time-series and CDF plots
"""
import pandas as pd
import numpy as np
import click
import matplotlib.pyplot as plt
import re
from datetime import datetime
import os

def parse_flow_log(log_file):
    """Parse TCP flow log file into structured data"""
    flows = []
    
    # Pattern to match: 2024-01-15 14:23:45,start=1705321425.123,end=1705321425.890,duration=0.767s
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),start=([0-9.]+),end=([0-9.]+),duration=([0-9.]+)s'
    
    try:
        with open(log_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                match = re.match(pattern, line)
                if match:
                    timestamp_str, start_time, end_time, duration = match.groups()
                    flows.append({
                        'timestamp': pd.to_datetime(timestamp_str),
                        'start_time': float(start_time),
                        'end_time': float(end_time),
                        'duration': float(duration)
                    })
                else:
                    print(f"Warning: Could not parse line {line_num}: {line}")
    
    except FileNotFoundError:
        print(f"File not found: {log_file}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error reading file {log_file}: {e}")
        return pd.DataFrame()
    
    if not flows:
        print("No valid flow data found")
        return pd.DataFrame()
    
    df = pd.DataFrame(flows)
    
    # Convert absolute start times to experiment-relative times
    if len(df) > 0:
        experiment_start = df['start_time'].min()
        df['start_relative'] = df['start_time'] - experiment_start
        df['end_relative'] = df['end_time'] - experiment_start
    
    return df

def generate_timeseries_plot(df, output_file=None):
    """Generate time-series plot of worst-case flow duration per second"""
    if len(df) == 0:
        print("No data for time-series plot")
        return
    
    # Group flows by start time (rounded to seconds)
    df['start_second'] = df['start_relative'].astype(int)
    
    # Calculate worst-case (maximum) duration for each second
    worst_case_per_second = df.groupby('start_second')['duration'].max()
    
    if len(worst_case_per_second) == 0:
        print("No grouped data for time-series plot")
        return
    
    # Create the plot
    plt.figure(figsize=(12, 6))
    plt.plot(worst_case_per_second.index, worst_case_per_second.values, 'b-', linewidth=2, marker='o', markersize=4)
    plt.grid(True, alpha=0.3)
    plt.xlabel('Time (seconds from experiment start)')
    plt.ylabel('Worst-case Flow Duration (seconds)')
    plt.title('TCP Flow Duration - Worst Case per Second')
    
    # Add summary statistics
    mean_worst = worst_case_per_second.mean()
    max_worst = worst_case_per_second.max()
    plt.axhline(y=mean_worst, color='red', linestyle='--', alpha=0.7, label=f'Mean: {mean_worst:.3f}s')
    plt.axhline(y=max_worst, color='orange', linestyle='--', alpha=0.7, label=f'Max: {max_worst:.3f}s')
    plt.legend()
    
    # Set reasonable y-axis limits
    plt.ylim(0, max_worst * 1.1)
    plt.xlim(worst_case_per_second.index.min(), worst_case_per_second.index.max())
    
    # Save or show
    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Time-series plot saved to: {output_file}")
    else:
        plt.show()
    
    plt.close()
    
    # Print summary
    print(f"\nTime-series Analysis:")
    print(f"  Time range: {worst_case_per_second.index.min()}-{worst_case_per_second.index.max()} seconds")
    print(f"  Active seconds: {len(worst_case_per_second)}")
    print(f"  Mean worst-case: {mean_worst:.3f}s")
    print(f"  Max worst-case: {max_worst:.3f}s")

def generate_cdf_plot(df, output_file=None):
    """Generate CDF plot for all flow durations"""
    if len(df) == 0:
        print("No data for CDF plot")
        return
    
    durations = df['duration'].values
    
    if len(durations) == 0:
        print("No duration data for CDF")
        return
    
    # Sort the data
    sorted_durations = np.sort(durations)
    
    # Calculate CDF values
    cdf = np.arange(1, len(sorted_durations) + 1) / len(sorted_durations)
    
    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.plot(sorted_durations, cdf, linewidth=2, color='blue')
    plt.grid(True, alpha=0.3)
    plt.xlabel('Flow Duration (seconds)')
    plt.ylabel('Cumulative Probability')
    plt.title('TCP Flow Duration - CDF')
    
    # Add percentile markers
    percentiles = [50, 90, 95, 99]
    for p in percentiles:
        if p <= 100:
            value = np.percentile(sorted_durations, p)
            plt.axhline(y=p/100, color='gray', linestyle='--', alpha=0.5)
            plt.axvline(x=value, color='gray', linestyle='--', alpha=0.5)
            plt.text(value, 0.05, f'P{p}: {value:.3f}s', rotation=90, 
                    verticalalignment='bottom', fontsize=8)
    
    # Set y-axis to 0-1
    plt.ylim(0, 1)
    plt.xlim(0, sorted_durations.max() * 1.05)
    
    # Save or show
    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"CDF plot saved to: {output_file}")
    else:
        plt.show()
    
    plt.close()
    
    # Print percentile summary
    print(f"\nFlow Duration Percentiles:")
    for p in [10, 25, 50, 75, 90, 95, 99]:
        value = np.percentile(sorted_durations, p)
        print(f"  P{p}: {value:.3f}s")

def analyze_tcp_flows(log_file, save_plots=False):
    """Analyze TCP flow log file"""
    try:
        # Check if file exists and is readable
        if not os.path.exists(log_file):
            print(f"File not found: {log_file}")
            return
        
        if os.path.getsize(log_file) == 0:
            print(f"Empty file: {log_file}")
            return
        
        # Parse the log file
        df = parse_flow_log(log_file)
        
        if len(df) == 0:
            print("No flow data to analyze")
            return
        
        # Basic statistics
        total_flows = len(df)
        experiment_duration = df['end_relative'].max() - df['start_relative'].min()
        
        print(f"\n=== TCP Flow Analysis ===")
        print(f"Total flows: {total_flows}")
        print(f"Experiment duration: {experiment_duration:.1f}s")
        print(f"Average flow rate: {total_flows/experiment_duration:.1f} flows/second")
        
        # Duration statistics
        mean_duration = df['duration'].mean()
        median_duration = df['duration'].median()
        max_duration = df['duration'].max()
        min_duration = df['duration'].min()
        
        print(f"\nFlow Duration Statistics:")
        print(f"  Mean: {mean_duration:.3f}s")
        print(f"  Median: {median_duration:.3f}s")
        print(f"  Min: {min_duration:.3f}s")
        print(f"  Max: {max_duration:.3f}s")
        
        # Generate plots
        base_filename = os.path.splitext(log_file)[0]
        
        # Time-series plot
        timeseries_output = f"{base_filename}_timeseries.png" if save_plots else None
        generate_timeseries_plot(df, timeseries_output)
        
        # CDF plot
        cdf_output = f"{base_filename}_cdf.png" if save_plots else None
        generate_cdf_plot(df, cdf_output)
        
    except Exception as e:
        print(f"Analysis error: {e}")
        import traceback
        traceback.print_exc()

@click.command()
@click.argument('log_file')
@click.option('--save-plots', is_flag=True, help='Save plots to files instead of displaying')
def main(log_file, save_plots):
    """Analyze TCP flow log data with time-series and CDF plots"""
    analyze_tcp_flows(log_file, save_plots)

if __name__ == "__main__":
    main()