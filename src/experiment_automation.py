#!/usr/bin/env python3
"""
Automated experiment runner for distributed iperf3 network testing
"""
import subprocess
import time
import csv
import os
import click
from datetime import datetime
from datastore import datastore

class ExperimentAutomation:
    def __init__(self, server_host="clem04", client_host="wash02", server_ip="192.168.1.1"):
        self.server_host = server_host
        self.client_host = client_host
        self.server_ip = server_ip
        self.results = []
        
    def run_ssh_command(self, host, command, log_file=None):
        """Run SSH command on remote host"""
        ssh_cmd = f"ssh {host} '{command}'"
        print(f"Running on {host}: {command}")
        
        try:
            if log_file:
                with open(log_file, 'a') as f:
                    f.write(f"\n[{datetime.now()}] SSH to {host}: {command}\n")
                    process = subprocess.Popen(ssh_cmd, shell=True, 
                                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                             universal_newlines=True)
                    for line in process.stdout:
                        print(line, end='')
                        f.write(line)
                    process.wait()
                    return process.returncode == 0
            else:
                result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print(f"Error: {result.stderr}")
                return result.returncode == 0
        except Exception as e:
            print(f"SSH command failed: {e}")
            return False
    
    def run_single_experiment(self, exp_id, duration=10, concurrency=4, interface="enp7s0np0", 
                            delay=10, port=5100, client_rate=1, transfer_size="2G", parallel=1, 
                            log_file=None):
        """Run a single distributed experiment"""
        print(f"\n=== Starting Experiment {exp_id} ===")
        if log_file:
            with open(log_file, 'a') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Experiment {exp_id} - {datetime.now()}\n")
                f.write(f"{'='*50}\n")
        
        # Step 1: Start server side
        server_cmd = f"source ~/indis/.venv/bin/activate && cd ~/indis/src && python3 experiment_orchestrator.py -t {duration} -c {concurrency} -i {interface} -o network_data.csv -d {delay} -p {port} --experiment-id {exp_id}"
        
        if not self.run_ssh_command(self.server_host, server_cmd, log_file):
            print(f"Failed to start server for experiment {exp_id}")
            return False
        
        # Step 2: Wait 2 seconds then start client
        time.sleep(2)
        
        client_cmd = f"source ~/indis/.venv/bin/activate && cd ~/indis/src && python3 experiment_client.py -t {duration} -c {client_rate} -s {transfer_size} -P {parallel} --server {self.server_ip} -p {port} --experiment-id {exp_id}"
        
        if not self.run_ssh_command(self.client_host, client_cmd, log_file):
            print(f"Failed to start client for experiment {exp_id}")
            return False
        
        # Step 3: Wait for experiment completion (2 * (duration + delay))
        wait_time = 2 * (duration + delay)
        print(f"Waiting {wait_time}s for experiment completion...")
        time.sleep(wait_time)
        
        # Step 4: Check datastore for results
        return self.check_experiment_results(exp_id)
    
    def check_experiment_results(self, exp_id):
        """Check if experiment results were saved to datastore"""
        # Copy datastore from server
        scp_cmd = f"scp {self.server_host}:~/indis/experiment_results.csv ./remote_results.csv"
        
        try:
            result = subprocess.run(scp_cmd, shell=True, capture_output=True)
            if result.returncode != 0:
                print(f"Failed to copy datastore from server")
                return False
            
            # Check if experiment ID exists in results
            if os.path.exists("./remote_results.csv"):
                with open("./remote_results.csv", 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('id', '').startswith(exp_id):
                            print(f"✅ Experiment {exp_id} results found:")
                            print(f"   ID: {row.get('id', 'N/A')}")
                            print(f"   Observed utilization: {row.get('Observed utilization', 'N/A')} Gbps")
                            print(f"   Total transfer time: {row.get('Total transfer time', 'N/A')} s")
                            self.results.append(row)
                            return True
            
            print(f"❌ No results found for experiment {exp_id}")
            return False
            
        except Exception as e:
            print(f"Error checking results: {e}")
            return False
    
    def print_all_results(self):
        """Print summary of all experiment results"""
        if not self.results:
            print("\nNo experiment results to display")
            return
        
        print(f"\n=== Experiment Results Summary ({len(self.results)} experiments) ===")
        print(f"{'ID':<20} {'Interface':<12} {'Duration':<8} {'Concur.':<6} {'Utilization':<12} {'Transfer Time':<15}")
        print("-" * 80)
        
        for result in self.results:
            print(f"{result.get('id', 'N/A'):<20} "
                  f"{result.get('interface', 'N/A'):<12} "
                  f"{result.get('duration', 'N/A'):<8} "
                  f"{result.get('Concur.', 'N/A'):<6} "
                  f"{result.get('Observed utilization', 'N/A'):<12} "
                  f"{result.get('Total transfer time', 'N/A'):<15}")
    
    def save_local_datastore(self, output_file="experiment_results_local.csv"):
        """Save collected results to local datastore"""
        if not self.results:
            print("No results to save")
            return
        
        with open(output_file, 'w', newline='') as f:
            if self.results:
                writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
                writer.writeheader()
                writer.writerows(self.results)
        
        print(f"Results saved to {output_file}")
    
    def load_experiment_config(self, config_file):
        """Load experiment configuration from CSV file"""
        experiments = []
        
        try:
            with open(config_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert string values to appropriate types
                    exp_config = {
                        'exp_id': row['exp_id'],
                        'duration': int(row.get('duration', 10)),
                        'concurrency': int(row.get('concurrency', 4)),
                        'interface': row.get('interface', 'enp7s0np0'),
                        'delay': int(row.get('delay', 10)),
                        'port': int(row.get('port', 5100)),
                        'client_rate': int(row.get('client_rate', 1)),
                        'transfer_size': row.get('transfer_size', '2G'),
                        'parallel': int(row.get('parallel', 1))
                    }
                    experiments.append(exp_config)
            
            print(f"Loaded {len(experiments)} experiments from {config_file}")
            return experiments
            
        except Exception as e:
            print(f"Error loading config file {config_file}: {e}")
            return []
    
    def run_experiment_config(self, config_file, log_file=None):
        """Run all experiments from configuration file"""
        experiments = self.load_experiment_config(config_file)
        if not experiments:
            print("No experiments to run")
            return
        
        print(f"Starting automated experiments: {len(experiments)} experiments")
        
        if log_file:
            with open(log_file, 'w') as f:
                f.write(f"Experiment Automation Log - {datetime.now()}\n")
                f.write(f"Server: {self.server_host}, Client: {self.client_host}\n")
                f.write(f"Config file: {config_file}\n")
        
        successful = 0
        failed = 0
        
        for exp_config in experiments:
            try:
                if self.run_single_experiment(log_file=log_file, **exp_config):
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Experiment {exp_config['exp_id']} failed with error: {e}")
                failed += 1
        
        print(f"\n=== Automation Complete ===")
        print(f"Successful: {successful}, Failed: {failed}")
        
        self.print_all_results()
        self.save_local_datastore()

@click.command()
@click.argument('config_file')
@click.option('--server-host', default='clem04', help='Server hostname')
@click.option('--client-host', default='wash02', help='Client hostname') 
@click.option('--server-ip', default='192.168.1.1', help='Server IP address')
@click.option('--log-file', help='Log file for experiment output')
def main(config_file, server_host, client_host, server_ip, log_file):
    """
    Automated experiment runner for distributed network testing
    
    CONFIG_FILE: CSV file with experiment configurations
    
    Example CSV format:
        exp_id,duration,concurrency,interface,delay,port,client_rate,transfer_size,parallel
        exp1,10,4,enp7s0np0,10,5100,1,2G,1
        exp2,30,8,enp7s0np0,15,5101,2,4G,2
    
    Examples:
        python3 experiment_automation.py experiments.csv
        python3 experiment_automation.py experiments.csv --log-file automation.log
    """
    
    automation = ExperimentAutomation(server_host, client_host, server_ip)
    automation.run_experiment_config(config_file, log_file)

if __name__ == "__main__":
    main()