#!/usr/bin/env bash
set -e

echo "=== Setting up AI Story Video Generation Harness on Ubuntu VPS ==="

# 1. System packages
apt-get update
apt-get install -y ffmpeg fonts-dejavu-core python3-pip python3-venv wget curl git

# 2. Configure 4GB Swap file if missing
if [ ! -f /swapfile ]; then
    echo "Creating 4GB swap space..."
    fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# 3. Install Ollama if missing
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

# 4. Pull lightweight Ollama model
echo "Pulling llama3.2:1b model..."
ollama pull llama3.2:1b

# 5. Setup Python virtual environment
cd /opt/ai-story-harness
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r backend/requirements.txt

# 6. Download Piper TTS model
mkdir -p models/piper
cd models/piper
wget -nc -q https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget -nc -q https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# 7. Setup systemd service
cp /opt/ai-story-harness/deployment/ai-story-backend.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable ai-story-backend.service
systemctl restart ai-story-backend.service

echo "=== Setup complete! Backend running on http://127.0.0.1:8000 ==="
