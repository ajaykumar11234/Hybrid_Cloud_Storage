#!/usr/bin/env bash
set -e

# Update ClamAV DB (may take a few seconds)
echo "🔄 Updating ClamAV DB..."
freshclam --quiet || echo "⚠️ freshclam failed (continuing)..."

# Start clamd (clamd daemon) in background
echo "🔄 Starting clamd..."
/usr/sbin/clamd &

# Wait a couple seconds for clamd to become available
sleep 2

# Start Gunicorn (4 workers)
echo "🚀 Starting Gunicorn..."
exec gunicorn -w 4 -b 0.0.0.0:8000 app:app
