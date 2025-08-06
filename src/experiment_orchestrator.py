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
    def __init__(self, duration, clients_per_second, interface, output_file, initial_port=5101, post_delay=60):
        self.duration = duration
        self.clients_per_second = clients_per_second
        self.interface = interface
        self.output_file = output_file
        self.initial_port = initial_port
        self.total_servers = duration * clients_per_second
        self.log_dir = f"experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.server_processes = []
        self.monitor_process = None
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
            cmd = [
                "iperf319", "-s", 
                "-p", str(port), 
                "-1",  # One connection then exit
                "-i", "1",  # 1 second intervals
                "--json",
                "--logfile", log_file
            ]
            
            try:
                process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.server_processes.append((process, port))
                
                if (i + 1) % 10 == 0:
                    print(f"  Started {i + 1}/{self.total_servers} servers...")
                    
            except Exception as e:
                print(f"Error starting server on port {port}: {e}")
                
        print(f"All {len(self.server_processes)} servers started (ports {self.initial_port}-{self.initial_port + self.total_servers - 1})")
        
    def start_network_monitor(self):
        """Start netmonitor.py subprocess"""
        monitor_output = f"{self.log_dir}/{self.output_file}"
        total_monitor_duration = self.duration + self.post_delay
        cmd = [
            "python3", "netmonitor.py",
            "-i", self.interface,
            "-d", str(total_monitor_duration),  # Monitor for duration + 60 seconds
            "-o", monitor_output
        ]
        
        print(f"\nStarting network monitor on interface {self.interface}...")
        print(f"Monitor output: {monitor_output}")
        
        try:
            self.monitor_process = subprocess.Popen(cmd)
            print("Network monitor started successfully")
        except Exception as e:
            print(f"Error starting network monitor: {e}")
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
            f"python3 analyze_netmonitor.py {self.log_dir}/{self.output_file} --save-plots -t {self.duration}",
            f"python3 analyze_iperf_json.py {self.log_dir}/iperf_logs/*.json -o {self.log_dir}/results/"
        ]
        for cmd in cmds:
            try:
                print(cmd)
                subprocess.run(cmd.split(), check=True)
            except:
                pass
        
    def cleanup(self):
        """Clean up processes"""
        print("\nCleaning up...")
        
        # Terminate monitor process
        if self.monitor_process and self.monitor_process.poll() is None:
            self.monitor_process.terminate()
            self.monitor_process.wait()
            
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
            self.start_network_monitor()
            time.sleep(2)  # Allow monitor to initialize
            
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
def main(duration, clients_per_second, interface, output, initial_port, delay):
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
        post_delay=delay
    )
    
    orchestrator.run()

if __name__ == "__main__":
    main()
