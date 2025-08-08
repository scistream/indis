#!/usr/bin/env python3
"""
Orchestrate network experiment with iperf3 servers and network monitoring
"""
import subprocess
import time
import os
import click
from datetime import datetime
from pathlib import Path
import signal
import sys

class ExperimentOrchestrator:
    def __init__(self, duration, clients_per_second, interface, output_file, initial_port=5101, post_delay=60, experiment_id=None):
        self.duration = duration
        self.clients_per_second = clients_per_second
        self.interface = interface
        self.output_file = output_file
        self.initial_port = initial_port
        self.total_servers = duration * clients_per_second
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_dir = f"experiment_{timestamp}"
        self.experiment_id = experiment_id
        self.server_processes = []
        self.monitor_process = None
        self.flow_monitor_process = None
        self.post_delay=post_delay
        
    def setup_directories(self):
        """Create directories for logs and results"""
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(f"{self.log_dir}/iperf_logs", exist_ok=True)
        print(f"Created experiment directory: {self.log_dir}")
        
    def start_iperf_servers(self):
        """Start c*t iperf3 servers"""
        print(f"\nStarting {self.total_servers} iperf3 servers...")
        
        for i in range(self.total_servers):
            port = self.initial_port + i
            log_file = f"{self.log_dir}/iperf_logs/server_{port}.json"
            
            # Start iperf3 server with JSON output
            cmd = f"iperf319 -s -p {port} -1 -i 1 --json --logfile {log_file}"
            
            try:
                process = subprocess.Popen(cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.server_processes.append((process, port))
                
                if (i + 1) % 10 == 0:
                    print(f"  Started {i + 1}/{self.total_servers} servers...")
                    
            except Exception as e:
                print(f"Error starting server on port {port}: {e}")
                
        print(f"All {len(self.server_processes)} servers started (ports {self.initial_port}-{self.initial_port + self.total_servers - 1})")
        
    def start_monitors(self):
        """Start monitoring subprocesses"""
        monitor_output = f"{self.log_dir}/{self.output_file}"
        flow_output = f"{self.log_dir}/tcp_flows.log"
        total_monitor_duration = self.duration + self.post_delay
        
        cmds = [
            (f"python3 netmonitor.py -i {self.interface} -d {total_monitor_duration} -o {monitor_output}", "network monitor", True),
            (f"python3 tcp_flow_monitor.py -d {total_monitor_duration} -i 0.1 -o {flow_output}", "TCP flow monitor", False)
        ]
        
        print(f"\nStarting monitors...")
        print(f"Network monitor output: {monitor_output}")
        print(f"Flow monitor output: {flow_output}")
        
        for cmd, name, critical in cmds:
            try:
                if name == "network monitor":
                    self.monitor_process = subprocess.Popen(cmd.split())
                else:
                    self.flow_monitor_process = subprocess.Popen(cmd.split())
                print(f"{name} started successfully")
            except Exception as e:
                print(f"Error starting {name}: {e}")
                if critical:
                    self.cleanup()
                    sys.exit(1)
            
    def wait_and_analyze(self):
        """Wait for experiment completion and run analysis"""
        total_wait = self.duration + self.post_delay
        print(f"\nExperiment running for {total_wait} seconds...")
        print(f"  Post-experiment delay: {self.post_delay}s")
        
        # Show progress
        for elapsed in range(0, total_wait, 10):
            remaining = total_wait - elapsed
            print(f"  Progress: {elapsed}/{total_wait}s (remaining: {remaining}s)")
            time.sleep(10)
            
        print("Experiment duration complete, waiting for processes to finish...")
        time.sleep(5)  # Extra buffer
        
    def run_analysis(self):
        print(f"\n=== Running Analysis ===")
        cmds = [
            f"python3 analyze_netmonitor.py {self.log_dir}/{self.output_file} --save-plots -t {self.duration} --experiment-id {self.experiment_id}",
            f"python3 analyze_iperf_json.py {self.log_dir}/iperf_logs/*.json -o {self.log_dir}/results/ --experiment-id {self.experiment_id}",
            f"python3 analyze_tcp_flows.py {self.log_dir}/tcp_flows.log --save-plots"
        ]
        
        # Save client experiment parameters
        if self.experiment_id:
            try:
                from datastore import datastore
                datastore.save_experiment(self.experiment_id, **{
                    'interface': self.interface,
                    'duration': self.duration, 
                    'Concur.': self.clients_per_second})
            except ImportError:
                pass
        for cmd in cmds:
            try:
                print(cmd)
                subprocess.run(cmd.split(), check=True)
            except:
                pass
        
    def cleanup(self):
        """Clean up processes"""
        print("\nCleaning up...")
        
        # Terminate monitor processes
        if self.monitor_process and self.monitor_process.poll() is None:
            self.monitor_process.terminate()
            self.monitor_process.wait()
            
        if self.flow_monitor_process and self.flow_monitor_process.poll() is None:
            self.flow_monitor_process.terminate()
            self.flow_monitor_process.wait()
            
        # Terminate any remaining server processes
        for process, port in self.server_processes:
            if process.poll() is None:
                process.terminate()
                
        print("Cleanup complete")
        
    def run(self):
        """Run the complete experiment"""
        print(f"=== Network Experiment Orchestrator ===")
        print(f"Duration: {self.duration}s")
        print(f"Clients per second: {self.clients_per_second}")
        print(f"Total servers needed: {self.total_servers}")
        print(f"Interface: {self.interface}")
        print(f"Output file: {self.output_file}")
        
        try:
            # Setup
            self.setup_directories()
            
            # Start servers
            self.start_iperf_servers()
            time.sleep(2)  # Allow servers to initialize
            
            # Start monitoring
            self.start_monitors()
            time.sleep(2)  # Allow monitors to initialize
            
            # Wait for experiment
            self.wait_and_analyze()
            
            # Print analysis instructions
            self.run_analysis()
            
            
        except KeyboardInterrupt:
            print("\nExperiment interrupted by user")
        finally:
            self.cleanup()

def signal_handler(sig, frame):
    print('\nReceived interrupt signal, cleaning up...')
    sys.exit(0)

@click.command()
@click.option('-t', '--duration', default=10, help='Experiment duration in seconds')
@click.option('-c', '--clients-per-second', default=1, help='Number of clients spawned per second')
@click.option('-i', '--interface', default='eth100', help='Network interface to monitor')
@click.option('-o', '--output', default='network_counters.csv', help='Output filename for network monitor')
@click.option('-p', '--initial-port', default=5101, help='Initial port number for iperf3 servers')
@click.option('-d', '--delay', default=10, help='Post-experiment monitoring delay in seconds')
@click.option('--experiment-id', help='Experiment ID for datastore')
def main(duration, clients_per_second, interface, output, initial_port, delay, experiment_id):
    """
    Orchestrate network experiment with iperf3 servers and monitoring
    
    This script will:
    1. Start c*t iperf3 servers
    2. Start network monitoring for t+d seconds
    3. Wait for experiment completion
    4. Provide commands for post-experiment analysis
    """
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create and run orchestrator
    orchestrator = ExperimentOrchestrator(
        duration=duration,
        clients_per_second=clients_per_second,
        interface=interface,
        output_file=output,
        initial_port=initial_port,
        post_delay=delay,
        experiment_id=experiment_id
    )
    
    orchestrator.run()

if __name__ == "__main__":
    main()
