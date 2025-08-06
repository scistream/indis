#!/usr/bin/env python3
"""
TCP Flow Monitor - tracks individual TCP connection lifecycles
"""
import time
import subprocess
import click

def get_current_flows():
    # Example using `ss` for demonstration purposes
    # Collects tuples of (src_ip, src_port, dst_ip, dst_port)
    result = subprocess.run(
        ["ss", "-tn"], capture_output=True, text=True
    )
    flows = set()
    for line in result.stdout.splitlines()[1:]:
        tokens = line.split()
        if len(tokens) < 5:
            continue
        local, remote = tokens[3], tokens[4]
        src_ip, src_port = local.rsplit(':', 1)
        dst_ip, dst_port = remote.rsplit(':', 1)
        flows.add((src_ip, src_port, dst_ip, dst_port))
    return flows

def run_flow_monitor(log_file, check_interval, duration):
    """Monitor TCP flows for specified duration"""
    observed_flows = {}  # (flow tuple) -> start_time
    completed_flows = []  # tuples: (flow, start_time, end_time, duration)

    print(f"Monitoring TCP flows for {duration}s -> {log_file}")
    with open(log_file, "a") as log:
        start_ts = time.time()
        while time.time() - start_ts < duration:
            loop_start_time = time.time()  # Start timing the loop
            
            now = time.time()
            current_flows = get_current_flows()
            
            # Register new flows with their start times
            for flow in current_flows:
                if flow not in observed_flows:
                    observed_flows[flow] = now  # record first seen time

            ended_flows_within_tick = []
            # Identify flows that have ended
            for flow in list(observed_flows.keys()):
                if flow not in current_flows:
                    start_time = observed_flows[flow]
                    if start_time >= start_ts:
                        end_time = now
                        duration = end_time - start_time
                        if end_time - now < check_interval:
                            ended_flows_within_tick.append(
                                (flow, start_time, end_time, duration)
                            )
                    del observed_flows[flow]
            
            # Log flows that ended within the last interval (simplified output)
            for flow_info in ended_flows_within_tick:
                flow, st, et, dur = flow_info
                log_line = (f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(et))},"
                            f"start={st:.3f},end={et:.3f},duration={dur:.3f}s\n")
                log.write(log_line)
                log.flush()
            
            # Calculate how long the loop took and adjust sleep time
            loop_duration = time.time() - loop_start_time
            sleep_time = max(0, check_interval - loop_duration)
            time.sleep(sleep_time)

@click.command()
@click.option('-d', '--duration', default=60, help='Duration in seconds')
@click.option('-i', '--interval', default=0.1, help='Check interval in seconds')
@click.option('-o', '--output', default='tcp_flows.log', help='Output log file')
def main(duration, interval, output):
    """TCP Flow Monitor - tracks individual TCP connection lifecycles"""
    
    run_flow_monitor(output, interval, duration)

if __name__ == "__main__":
    main()
