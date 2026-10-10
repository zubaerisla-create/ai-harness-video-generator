#!/bin/bash
set -e

echo "=== [CI/CD] Starting Deployment on Hostinger VPS ==="
cd /opt/ai-story-harness

# Ensure git repository is configured
if [ ! -d ".git" ]; then
    echo "Initializing git tracking..."
    git init
    git remote add origin https://github.com/zubaerisla-create/ai-harness-video-generator.git || true
fi

# Clean any stale lock files
rm -f .git/index.lock .git/FETCH_HEAD.lock

echo "Fetching latest changes from origin/main..."
git fetch origin main
git reset --hard origin/main

# Ensure runtime directories exist
mkdir -p outputs/tmp backend/data models/piper

echo "Restarting backend service..."
systemctl daemon-reload
systemctl restart ai-story-backend.service

echo "Updating frontend dependencies and building production assets..."
cd /opt/ai-story-harness/frontend
npm install --prefer-offline --no-audit
npm run build

echo "Reloading frontend service with PM2..."
pm2 restart ai-story-frontend || pm2 start npm --name "ai-story-frontend" -- start

echo "Verifying live HTTP responses..."
sleep 2
curl -s -o /dev/null -w "Home (3000): %{http_code}\n" http://127.0.0.1:3000/
curl -s -o /dev/null -w "Studio (3000): %{http_code}\n" http://127.0.0.1:3000/studio
curl -s -o /dev/null -w "Queue (3000): %{http_code}\n" http://127.0.0.1:3000/queue
curl -s -o /dev/null -w "Backend API (8000): %{http_code}\n" http://127.0.0.1:8000/api/system/health

echo "=== [CI/CD] Deployment Succeeded! Live at http://31.97.180.176/ ==="
