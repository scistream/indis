# Network Performance Testing Framework

A distributed system for conducting controlled iperf3 network performance experiments with real-time monitoring and analysis.

## Quick Start

**Server side:**
```bash
python3 src/experiment_orchestrator.py -t 30 -c 4 -i eth0 -o network_data.csv
```

**Client side:**
```bash
python3 src/experiment_client.py -t 30 -c 4 -s 1G --server <server_ip>
```

## Requirements
- `iperf319` binary (custom version)
- Python dependencies: click, psutil, pandas, numpy, matplotlib

## Monitoring Scripts

The framework includes two monitoring scripts that capture different aspects of network behavior. **netmonitor.py** provides interface-level aggregate metrics by sampling network counters (bytes, packets, errors, drops) every second using psutil, generating CSV time-series data suitable for throughput and utilization analysis. **tcp_flow_monitor.py** tracks individual TCP connection lifecycles by monitoring active flows every 0.1 seconds using the `ss` command, logging per-connection start/end times and durations to analyze connection patterns and flow completion behavior.

Analysis scripts:
    - analyze_netmonitor.py
    - analyze_iperf_json.py

# TODO

- Configuration file support using click-extra (TOML/YAML configs)
- Installation script + instructions
- Host tuning scripts
- Extend underlying implementation
    - gridftp
    - ZMQ?
    - nanomsg?
- Unit tests for analysis scripts
- integration tests for experiment and auxiliary scripts?