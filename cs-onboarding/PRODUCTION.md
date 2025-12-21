# CS Onboarding - Production Deployment Guide

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- Redis 6+ (optional but recommended)

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables (copy `.env.example` to `.env`):
```bash
# Required
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Optional but recommended
REDIS_URL=redis://localhost:6379/0
```

3. Run database migrations:
```bash
alembic upgrade head
```

## 🏃 Running the Application

### Development Mode
```bash
python run.py
```

### Production Mode (Recommended)
```bash
# Linux/Mac
chmod +x start_production.sh
./start_production.sh

# Windows
start_production.bat
```

### Custom Configuration
```bash
# Set number of workers (default: 4)
export GUNICORN_WORKERS=8

# Set port (default: 5000)
export PORT=8000

# Set log level (default: info)
export LOG_LEVEL=debug

./start_production.sh
```

## 🔧 Configuration

### Gunicorn Settings
Edit `gunicorn_config.py` to customize:
- Number of workers
- Timeout settings
- Logging format
- SSL configuration

### Rate Limiting
Default limits (can be customized in `backend/project/config/rate_limit_config.py`):
- 200 requests per day
- 50 requests per hour
- Login: 5 requests per minute

### Database Connection Pool
Current settings (in `backend/project/database/db_pool.py`):
- Minimum connections: 10
- Maximum connections: 50
- Suitable for 30+ concurrent users

## 📊 Monitoring

### Health Check Endpoints
- `/health` - Full health check (database + Redis)
- `/health/ready` - Readiness check
- `/health/live` - Liveness check

Example:
```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "healthy",
  "checks": {
    "database": {"status": "healthy", "type": "postgres"},
    "redis": {"status": "healthy"}
  }
}
```

## 💾 Database Backup

### Manual Backup
```bash
python backup_database.py
```

### Automated Backup (Cron)
Add to crontab:
```bash
# Daily backup at 2 AM
0 2 * * * cd /path/to/cs-onboarding && python backup_database.py >> /var/log/cs-backup.log 2>&1
```

Backups are stored in `./backups/` and automatically cleaned up after 7 days.

## 🔒 Security

### Rate Limiting
Automatically protects against:
- Brute force attacks
- DDoS attempts
- API abuse

### HTTPS
For production, configure SSL in `gunicorn_config.py`:
```python
keyfile = '/path/to/private.key'
certfile = '/path/to/certificate.crt'
```

## 📈 Performance

### Recommended Infrastructure (30+ users)
- **CPU**: 2-4 vCPUs
- **RAM**: 4-8 GB
- **Disk**: 20-50 GB SSD
- **PostgreSQL**: 50-100 max connections
- **Redis**: 512 MB - 1 GB

### Scaling
To handle more users:
1. Increase Gunicorn workers: `GUNICORN_WORKERS=8`
2. Increase database pool: Edit `db_pool.py`
3. Add load balancer for multiple instances

## 🐛 Troubleshooting

### Application won't start
- Check environment variables in `.env`
- Verify database connection
- Check logs for errors

### High memory usage
- Reduce number of Gunicorn workers
- Check for memory leaks in application code
- Monitor with `htop` or similar

### Slow responses
- Check database query performance
- Verify Redis is running
- Monitor with `/health` endpoint

## 📝 Logs

Logs are written to stdout/stderr. To save to file:
```bash
./start_production.sh >> app.log 2>&1
```

## 🔄 Updates

1. Pull latest code
2. Install new dependencies: `pip install -r requirements.txt`
3. Run migrations: `alembic upgrade head`
4. Restart application

## 📞 Support

For issues or questions, check:
- Application logs
- Health check endpoint
- Database connection
- Redis connection
