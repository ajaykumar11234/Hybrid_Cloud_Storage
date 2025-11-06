#!/usr/bin/env bash
set -e

echo "=========================================="
echo "🚀 Starting Flask Backend (Hybrid Storage)"
echo "=========================================="
echo "Environment:"
echo "  🌍 PORT=${PORT:-8000}"
echo "  🧠 FLASK_ENV=${FLASK_ENV:-production}"
echo "------------------------------------------"

# Start Gunicorn with app factory
exec gunicorn -w 4 -b 0.0.0.0:${PORT:-8000} 'app:create_app()'
