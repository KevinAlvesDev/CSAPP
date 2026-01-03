@echo off
REM Production startup script for CS Onboarding (Windows)
REM Uses Gunicorn with optimal settings for 30+ concurrent users

echo ============================================
echo Starting CS Onboarding (Production Mode)
echo ============================================

REM Set default values if not already set
if not defined PORT set PORT=5000
if not defined GUNICORN_WORKERS set GUNICORN_WORKERS=4
if not defined LOG_LEVEL set LOG_LEVEL=info

echo Port: %PORT%
echo Workers: %GUNICORN_WORKERS%
echo Log Level: %LOG_LEVEL%
echo ============================================

REM Start Gunicorn
gunicorn ^
    --config gunicorn_config.py ^
    --bind 0.0.0.0:%PORT% ^
    --workers %GUNICORN_WORKERS% ^
    --timeout 120 ^
    --log-level %LOG_LEVEL% ^
    --access-logfile - ^
    --error-logfile - ^
    run:app
