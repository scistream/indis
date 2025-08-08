#!/bin/bash
set -e

# Install uv if not present
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Create venv and install dependencies
uv sync

# Install iperf319
echo "Installing iperf319..."
sudo apt-get update && sudo apt-get install -y build-essential
wget https://downloads.es.net/pub/iperf/iperf-3.19.1.tar.gz
tar -xf iperf-3.19.1.tar.gz
cd iperf-3.19.1/
./configure && make && sudo make install
sudo ln -sf ~/iperf-3.19.1/src/iperf3 /usr/local/bin/iperf319
iperf319 --version

echo "Installation complete. Activate with: source .venv/bin/activate"