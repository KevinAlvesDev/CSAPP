#!/bin/bash
# Production startup script for CS Onboarding
# Uses Gunicorn with optimal settings for 30+ concurrent users

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set default values
export PORT=${PORT:-5000}
export GUNICORN_WORKERS=${GUNICORN_WORKERS:-4}
export LOG_LEVEL=${LOG_LEVEL:-info}

echo "============================================"
echo "Starting CS Onboarding (Production Mode)"
echo "============================================"
echo "Port: $PORT"
echo "Workers: $GUNICORN_WORKERS"
echo "Log Level: $LOG_LEVEL"
echo "============================================"

# Start Gunicorn
gunicorn \
    --config gunicorn_config.py \
    --bind 0.0.0.0:$PORT \
    --workers $GUNICORN_WORKERS \
    --timeout 120 \
    --log-level $LOG_LEVEL \
    --access-logfile - \
    --error-logfile - \
    run:app
