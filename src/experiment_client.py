#!/usr/bin/env python3
"""
Experiment client that spawns iperf3 clients at a controlled rate
"""
import subprocess
import time
import os
import click
from datetime import datetime
from pathlib import Path
import signal
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class ExperimentClient:
    def __init__(self, duration, clients_per_second, transfer_size, parallel_flows, 
                 server_ip, initial_port, experiment_id=None):
        self.duration = duration
        self.clients_per_second = clients_per_second
        self.transfer_size = transfer_size
        self.parallel_flows = parallel_flows
        self.server_ip = server_ip
        self.initial_port = initial_port
        self.experiment_id = experiment_id
        self.log_dir = f"client_experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_port = initial_port
        self.active_processes = []
        self.stop_event = threading.Event()
        
    def setup_directories(self):
        """Create directories for logs"""
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(f"{self.log_dir}/client_logs", exist_ok=True)
        print(f"Created client experiment directory: {self.log_dir}")
        
    def start_iperf_client(self, port, batch_num, client_num):
        """Start a single iperf3 client"""
        cpu_id = port % 30  # Alternate through 30 CPUs based on port
        
        log_file = f"{self.log_dir}/client_logs/client_b{batch_num}_c{client_num}_p{port}.json"
        
        cmd = [
            "iperf319",
            "-c", self.server_ip,
            "--port", str(port),
            "-n", self.transfer_size,  # Transfer size (e.g., "0.1G")
            "-P", str(self.parallel_flows),  # Parallel flows
            "-i", "0.1",  # 1 second intervals
#            "-A", f"{cpu_id},{cpu_id}",  # CPU affinity
            "--json"
        ]
        
        try:
            # Start the client and save output to file
            with open(log_file, 'w') as f:
                process = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
                return process, port, log_file
        except Exception as e:
            print(f"Error starting client for port {port}: {e}")
            return None, port, None
            
    def spawn_client_batch(self, batch_num):
        """Spawn a batch of c concurrent clients"""
        batch_start_time = time.time()
        print(f"\n[Batch {batch_num}] Starting {self.clients_per_second} clients at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
        batch_processes = []
        stagger_delay = 1.0 / (self.clients_per_second + 1)  # Divide 1 second into c+1 parts
        
        with ThreadPoolExecutor(max_workers=self.clients_per_second) as executor:
            futures = []
            
            for client_num in range(self.clients_per_second):
                port = self.current_port
                self.current_port += 1
                
                # Submit client start task
                future = executor.submit(self.start_iperf_client, port, batch_num, client_num)
                futures.append(future)
                time.sleep(stagger_delay)
            
            for future in as_completed(futures):
                process, port, log_file = future.result()
                if process:
                    batch_processes.append((process, port, log_file))
                    print(f"  Started client → {self.server_ip}:{port} (PID: {process.pid})")
        
        batch_spawn_duration = time.time() - batch_start_time
        print(f"[Batch {batch_num}] Spawned {len(batch_processes)} clients in {batch_spawn_duration:.3f}s (stagger: {stagger_delay*1000:.0f}ms)")
        
        return batch_processes, batch_spawn_duration
        
    def run_experiment(self):
        """Run the experiment with compensating sleep strategy"""
        print(f"\n=== Starting Client Experiment ===")
        print(f"Duration: {self.duration}s")
        print(f"Clients per second: {self.clients_per_second}")
        print(f"Transfer size per client: {self.transfer_size}")
        print(f"Parallel flows per client: {self.parallel_flows}")
        print(f"Target server: {self.server_ip}")
        print(f"Starting port: {self.initial_port}")
        print(f"Total clients to spawn: {self.duration * self.clients_per_second}")
        
        experiment_start_time = time.time()
        
        for batch_num in range(self.duration):
            if self.stop_event.is_set():
                print("\nExperiment interrupted")
                break
                
            batch_target_time = experiment_start_time + batch_num
            current_time = time.time()
            
            # Check if we're running behind schedule
            if current_time > batch_target_time + 1.0:
                print(f"\n[WARNING] Running behind schedule by {current_time - batch_target_time:.3f}s")
            
            # Spawn the batch
            batch_processes, spawn_duration = self.spawn_client_batch(batch_num + 1)
            self.active_processes.extend(batch_processes)
            
            # Calculate compensating sleep time
            next_batch_time = experiment_start_time + (batch_num + 1)
            current_time = time.time()
            sleep_time = max(0, next_batch_time - current_time)
            
            if batch_num < self.duration - 1:  # Don't sleep after last batch
                if sleep_time > 0:
                    print(f"  Sleeping for {sleep_time:.3f}s until next batch")
                    time.sleep(sleep_time)
                    print(current_time)
                else:
                    print(f"  No sleep needed, running {-sleep_time:.3f}s behind schedule")
        
        experiment_end_time = time.time()
        total_duration = experiment_end_time - experiment_start_time
        
        print(f"\n=== Client Spawning Complete ===")
        print(f"Total experiment duration: {total_duration:.2f}s")
        print(f"Target duration: {self.duration}s")
        print(f"Total clients spawned: {len(self.active_processes)}")
        
        # Wait for all clients to complete
        print("\nWaiting for all clients to finish transfers...")
        self.wait_for_clients()
        
    def wait_for_clients(self):
        """Wait for all client processes to complete"""
        start_wait = time.time()
        total_clients = len(self.active_processes)
        completed = 0
        
        while self.active_processes and not self.stop_event.is_set():
            remaining_processes = []
            
            for process, port, log_file in self.active_processes:
                if process.poll() is None:
                    remaining_processes.append((process, port, log_file))
                else:
                    completed += 1
            
            self.active_processes = remaining_processes
            
            if self.active_processes:
                elapsed = time.time() - start_wait
                print(f"\rClients completed: {completed}/{total_clients} "
                      f"(Active: {len(self.active_processes)}, Elapsed: {elapsed:.1f}s)", 
                      end='', flush=True)
                time.sleep(1)
        
        print(f"\n\nAll clients completed!")
        
        # Save client parameters to datastore
        if self.experiment_id:
            try:
                from datastore import datastore
                datastore.save_experiment(self.experiment_id, **{
                    'Parallel.': self.parallel_flows,
                    'size': self.transfer_size,
                    'Freq': self.clients_per_second
                })
            except ImportError:
                pass
        
    def cleanup(self):
        """Clean up any remaining processes"""
        if self.active_processes:
            print("\nTerminating remaining client processes...")
            for process, _, _ in self.active_processes:
                if process.poll() is None:
                    process.terminate()
                    
    def signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        print("\n\nReceived interrupt signal, stopping experiment...")
        self.stop_event.set()
        self.cleanup()
        sys.exit(0)
        
    def run(self):
        """Run the complete experiment with signal handling"""
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            self.setup_directories()
            self.run_experiment()
            
            print(f"\n=== Experiment Complete ===")
            print(f"Client logs saved in: {self.log_dir}/client_logs/")
            print(f"\nTo analyze results:")
            print(f"  python3 analyze_iperf_json.py \"{self.log_dir}/client_logs/*.json\"")
            
        except Exception as e:
            print(f"\nExperiment failed: {e}")
            self.cleanup()
            raise

@click.command()
@click.option('-t', '--duration', default=10, help='Experiment duration in seconds')
@click.option('-c', '--clients-per-second', default=8, help='Number of concurrent clients per second')
@click.option('-s', '--size', default='0.1G', help='Transfer size per client (e.g., 0.1G, 100M)')
@click.option('-P', '--parallel', default=4, help='Number of parallel flows per client')
@click.option('--server', default='localhost', help='iPerf3 server IP address')
@click.option('-p', '--initial-port', default=5101, help='Initial port number')
@click.option('--experiment-id', help='Experiment ID for datastore')
def main(duration, clients_per_second, size, parallel, server, initial_port, experiment_id):
    """
    Experiment client that spawns iperf3 clients at a controlled rate
    
    Every second, spawns c concurrent iperf3 clients, each connecting to a 
    different sequential port on the server.
    
    Examples:
        # Default: 10s experiment, 8 clients/sec, 0.1GB transfers
        ./experiment_client.py
        
        # Custom configuration
        ./experiment_client.py -t 30 -c 4 -s 1G --server 10.0.0.1
        
        # High rate experiment
        ./experiment_client.py -t 60 -c 16 -s 50M -P 8
    """
    
    client = ExperimentClient(
        duration=duration,
        clients_per_second=clients_per_second,
        transfer_size=size,
        parallel_flows=parallel,
        server_ip=server,
        initial_port=initial_port,
        experiment_id=experiment_id
    )
    
    client.run()

if __name__ == "__main__":
    main()