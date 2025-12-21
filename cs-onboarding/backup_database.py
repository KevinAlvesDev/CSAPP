#!/usr/bin/env python3
"""
Database Backup Script for CS Onboarding
Creates compressed backups of PostgreSQL database

Usage:
    python backup_database.py

Environment variables required:
    - DB_HOST
    - DB_PORT
    - DB_NAME
    - DB_USER
    - DB_PASSWORD
    - BACKUP_DIR (optional, defaults to ./backups)
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_backup():
    """Create a compressed backup of the PostgreSQL database."""
    
    # Get database credentials from environment
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    
    # Validate required environment variables
    if not all([db_host, db_name, db_user, db_password]):
        print("ERROR: Missing required environment variables")
        print("Required: DB_HOST, DB_NAME, DB_USER, DB_PASSWORD")
        sys.exit(1)
    
    # Create backup directory
    backup_dir = Path(os.getenv('BACKUP_DIR', './backups'))
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f"cs_onboarding_backup_{timestamp}.sql.gz"
    
    print(f"Creating backup: {backup_file}")
    print(f"Database: {db_name}@{db_host}:{db_port}")
    
    # Set PGPASSWORD environment variable for pg_dump
    env = os.environ.copy()
    env['PGPASSWORD'] = db_password
    
    try:
        # Run pg_dump and compress with gzip
        dump_command = [
            'pg_dump',
            '-h', db_host,
            '-p', db_port,
            '-U', db_user,
            '-d', db_name,
            '--no-owner',
            '--no-acl',
            '-v'
        ]
        
        gzip_command = ['gzip', '-c']
        
        # Execute pg_dump | gzip > backup_file
        with open(backup_file, 'wb') as f:
            dump_process = subprocess.Popen(
                dump_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            gzip_process = subprocess.Popen(
                gzip_command,
                stdin=dump_process.stdout,
                stdout=f,
                stderr=subprocess.PIPE
            )
            
            dump_process.stdout.close()
            gzip_output, gzip_error = gzip_process.communicate()
            dump_output, dump_error = dump_process.communicate()
        
        # Check for errors
        if dump_process.returncode != 0:
            print(f"ERROR: pg_dump failed")
            print(dump_error.decode())
            sys.exit(1)
        
        if gzip_process.returncode != 0:
            print(f"ERROR: gzip failed")
            print(gzip_error.decode())
            sys.exit(1)
        
        # Get backup file size
        file_size = backup_file.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        print(f"✅ Backup created successfully!")
        print(f"   File: {backup_file}")
        print(f"   Size: {file_size_mb:.2f} MB")
        
        # Clean up old backups (keep last 7 days)
        cleanup_old_backups(backup_dir, days_to_keep=7)
        
        return True
        
    except FileNotFoundError:
        print("ERROR: pg_dump not found. Please install PostgreSQL client tools.")
        print("  Ubuntu/Debian: sudo apt-get install postgresql-client")
        print("  macOS: brew install postgresql")
        print("  Windows: Install from https://www.postgresql.org/download/windows/")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Backup failed: {e}")
        sys.exit(1)


def cleanup_old_backups(backup_dir, days_to_keep=7):
    """Remove backups older than specified days."""
    from datetime import timedelta
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    removed_count = 0
    for backup_file in backup_dir.glob('cs_onboarding_backup_*.sql.gz'):
        # Extract timestamp from filename
        try:
            timestamp_str = backup_file.stem.split('_')[-2] + '_' + backup_file.stem.split('_')[-1]
            file_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            
            if file_date < cutoff_date:
                backup_file.unlink()
                removed_count += 1
                print(f"   Removed old backup: {backup_file.name}")
        except (ValueError, IndexError):
            # Skip files that don't match expected format
            continue
    
    if removed_count > 0:
        print(f"   Cleaned up {removed_count} old backup(s)")


if __name__ == '__main__':
    print("=" * 60)
    print("CS Onboarding - Database Backup")
    print("=" * 60)
    create_backup()
    print("=" * 60)
