# VinFlow Deployment Guide for Vultr Server

This comprehensive guide will walk you through deploying your VinFlow Django application on a Vultr VPS server.

## Table of Contents

1. [Server Requirements](#server-requirements)
2. [Initial Server Setup](#initial-server-setup)
3. [Install Dependencies](#install-dependencies)
4. [Database Setup](#database-setup)
5. [Application Setup](#application-setup)
6. [Web Server Configuration](#web-server-configuration)
7. [SSL Certificate Setup](#ssl-certificate-setup)
8. [Service Configuration](#service-configuration)
9. [Deployment](#deployment)
10. [Monitoring and Maintenance](#monitoring-and-maintenance)
11. [Troubleshooting](#troubleshooting)

---

## Server Requirements

### Recommended Specifications

- **OS**: Ubuntu 22.04 LTS or Ubuntu 24.04 LTS
- **RAM**: Minimum 2GB (4GB+ recommended)
- **CPU**: 2+ cores
- **Storage**: 40GB+ SSD
- **Plan**: Vultr Cloud Compute ($12/month or higher)

### Software Requirements

- Python 3.10+
- PostgreSQL 14+
- Redis 6+
- Nginx
- Git

---

## Initial Server Setup

### 1. Create Vultr Instance

1. Log into your Vultr account
2. Deploy new instance
3. Choose **Ubuntu 22.04 LTS** or **24.04 LTS**
4. Select server location closest to your users
5. Select plan (minimum $12/month)
6. Add SSH key or use password
7. Deploy server

### 2. Connect to Server

```bash
ssh root@your-server-ip
```

### 3. Update System

```bash
apt update && apt upgrade -y
```

### 4. Create Non-Root User (Optional but Recommended)

```bash
adduser vinflow
usermod -aG sudo vinflow
```

### 5. Configure Firewall

```bash
# Install UFW if not installed
apt install ufw -y

# Allow SSH
ufw allow OpenSSH

# Allow HTTP and HTTPS
ufw allow 'Nginx Full'

# Enable firewall
ufw enable
ufw status
```

---

## Install Dependencies

### 1. Install Python and System Dependencies

```bash
apt install -y python3 python3-pip python3-venv python3-dev
apt install -y build-essential libpq-dev libssl-dev libffi-dev
apt install -y git curl wget nano
```

### 2. Install PostgreSQL

```bash
# Install PostgreSQL
apt install -y postgresql postgresql-contrib

# Start PostgreSQL
systemctl start postgresql
systemctl enable postgresql
```

### 3. Install Redis

```bash
# Install Redis
apt install -y redis-server

# Configure Redis
nano /etc/redis/redis.conf
# Change: supervised no -> supervised systemd

# Restart Redis
systemctl restart redis
systemctl enable redis

# Test Redis
redis-cli ping
# Should return: PONG
```

### 4. Install Nginx

```bash
apt install -y nginx

# Start Nginx
systemctl start nginx
systemctl enable nginx
```

---

## Database Setup

### 1. Create PostgreSQL Database and User

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL shell, run:
CREATE DATABASE vinflow_production;
CREATE USER vinflow_user WITH PASSWORD 'your-strong-password-here';

# Grant privileges
ALTER ROLE vinflow_user SET client_encoding TO 'utf8';
ALTER ROLE vinflow_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE vinflow_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE vinflow_production TO vinflow_user;

# Exit PostgreSQL
\q
```

### 2. Test Database Connection

```bash
psql -U vinflow_user -d vinflow_production -h localhost
# Enter password when prompted
# \q to exit
```

---

## Application Setup

### 1. Create Project Directory

```bash
mkdir -p /var/www/vinflow
cd /var/www/vinflow
```

### 2. Clone Your Repository

```bash
# If using Git
git clone https://github.com/yourusername/vinflow.git .

# Or upload files via SCP/SFTP
# scp -r /path/to/local/vinflow root@your-server-ip:/var/www/
```

### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn  # If not in requirements.txt
```

### 5. Configure Environment Variables

```bash
# Copy production environment template
cp deploy/env.production .env

# Edit .env file
nano .env
```

Update the following in `.env`:

```bash
# Generate strong SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

SECRET_KEY=your-generated-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-server-ip

# Database
DB_NAME=vinflow_production
DB_USER=vinflow_user
DB_PASSWORD=your-database-password
DB_HOST=localhost
DB_PORT=5432

# Update payment gateway URLs
PAYPAL_RETURN_URL=https://your-domain.com/panel/payment/paypal/return/
KHQR_CALLBACK_URL=https://your-domain.com/panel/payment/khqr/callback/
# ... etc
```

### 6. Run Migrations

```bash
python manage.py migrate
```

### 7. Create Superuser

```bash
python manage.py createsuperuser
```

### 8. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### 9. Compile Translation Messages

```bash
python manage.py compilemessages
```

### 10. Create Required Directories

```bash
# Create log directory
mkdir -p /var/log/vinflow

# Create run directory for PID files
mkdir -p /var/run/vinflow

# Set ownership
chown -R www-data:www-data /var/www/vinflow
chown -R www-data:www-data /var/log/vinflow
chown -R www-data:www-data /var/run/vinflow
```

---

## Web Server Configuration

### 1. Configure Nginx

```bash
# Copy nginx configuration
cp /var/www/vinflow/deploy/nginx.conf /etc/nginx/sites-available/vinflow

# Edit configuration
nano /etc/nginx/sites-available/vinflow
```

Update the following in nginx configuration:
- Replace `your-domain.com` with your actual domain
- Update SSL certificate paths (we'll add these next)

```bash
# Create symlink
ln -s /etc/nginx/sites-available/vinflow /etc/nginx/sites-enabled/

# Remove default site
rm /etc/nginx/sites-enabled/default

# Test nginx configuration
nginx -t

# If OK, reload nginx
systemctl reload nginx
```

---

## SSL Certificate Setup

### Using Let's Encrypt (Free)

```bash
# Install Certbot
apt install -y certbot python3-certbot-nginx

# Create directory for ACME challenge
mkdir -p /var/www/certbot

# Temporarily modify nginx to allow HTTP
nano /etc/nginx/sites-available/vinflow
# Comment out SSL lines temporarily

# Reload nginx
systemctl reload nginx

# Get SSL certificate
certbot --nginx -d your-domain.com -d www.your-domain.com

# Certbot will automatically configure nginx
# Follow the prompts

# Test auto-renewal
certbot renew --dry-run
```

### Auto-renewal Setup

Certbot automatically creates a systemd timer. Verify:

```bash
systemctl list-timers | grep certbot
```

---

## Service Configuration

### 1. Setup Gunicorn Service

```bash
# Copy service file
cp /var/www/vinflow/deploy/gunicorn.service /etc/systemd/system/vinflow-gunicorn.service

# Edit if needed
nano /etc/systemd/system/vinflow-gunicorn.service

# Reload systemd
systemctl daemon-reload

# Start and enable service
systemctl start vinflow-gunicorn
systemctl enable vinflow-gunicorn

# Check status
systemctl status vinflow-gunicorn
```

### 2. Setup Celery Worker Service

```bash
# Copy service file
cp /var/www/vinflow/deploy/celery.service /etc/systemd/system/vinflow-celery.service

# Reload systemd
systemctl daemon-reload

# Start and enable service
systemctl start vinflow-celery
systemctl enable vinflow-celery

# Check status
systemctl status vinflow-celery
```

### 3. Setup Celery Beat Service

```bash
# Copy service file
cp /var/www/vinflow/deploy/celerybeat.service /etc/systemd/system/vinflow-celerybeat.service

# Reload systemd
systemctl daemon-reload

# Start and enable service
systemctl start vinflow-celerybeat
systemctl enable vinflow-celerybeat

# Check status
systemctl status vinflow-celerybeat
```

---

## Deployment

### 1. Make Deploy Script Executable

```bash
chmod +x /var/www/vinflow/deploy/deploy.sh
```

### 2. Initial Manual Deployment

Test all services manually first:

```bash
# Check all services
systemctl status vinflow-gunicorn
systemctl status vinflow-celery
systemctl status vinflow-celerybeat
systemctl status nginx
systemctl status redis
systemctl status postgresql
```

### 3. Test Application

```bash
# Visit your domain
https://your-domain.com

# Check logs if issues
tail -f /var/log/vinflow/gunicorn-error.log
tail -f /var/log/nginx/vinflow-error.log
```

### 4. Future Deployments

For code updates, use the deploy script:

```bash
cd /var/www/vinflow
sudo ./deploy/deploy.sh
```

---

## Monitoring and Maintenance

### 1. View Logs

```bash
# Gunicorn logs
tail -f /var/log/vinflow/gunicorn-access.log
tail -f /var/log/vinflow/gunicorn-error.log

# Celery logs
tail -f /var/log/vinflow/celery-worker.log
tail -f /var/log/vinflow/celery-beat.log

# Nginx logs
tail -f /var/log/nginx/vinflow-access.log
tail -f /var/log/nginx/vinflow-error.log

# System logs
journalctl -u vinflow-gunicorn -f
journalctl -u vinflow-celery -f
```

### 2. Database Backup

```bash
# Manual backup
pg_dump -U vinflow_user -h localhost vinflow_production > backup_$(date +%Y%m%d).sql
gzip backup_$(date +%Y%m%d).sql

# Automate with cron (daily backup at 2 AM)
crontab -e
# Add:
0 2 * * * pg_dump -U vinflow_user -h localhost vinflow_production | gzip > /var/backups/vinflow/backup_$(date +\%Y\%m\%d).sql.gz
```

### 3. Monitor Server Resources

```bash
# Install htop
apt install htop -y
htop

# Check disk usage
df -h

# Check memory
free -m

# Check running processes
ps aux | grep gunicorn
ps aux | grep celery
```

### 4. Update Application

```bash
# Pull latest code
cd /var/www/vinflow
git pull origin main

# Run deployment script
sudo ./deploy/deploy.sh
```

---

## Troubleshooting

### Common Issues

#### 1. 502 Bad Gateway

**Cause**: Gunicorn not running or socket issue

**Solution**:
```bash
systemctl status vinflow-gunicorn
systemctl restart vinflow-gunicorn
journalctl -u vinflow-gunicorn -n 50
```

#### 2. Static Files Not Loading

**Cause**: Permissions or collectstatic not run

**Solution**:
```bash
cd /var/www/vinflow
source venv/bin/activate
python manage.py collectstatic --noinput
chown -R www-data:www-data /var/www/vinflow/staticfiles
```

#### 3. Database Connection Failed

**Cause**: Wrong credentials or PostgreSQL not running

**Solution**:
```bash
systemctl status postgresql
psql -U vinflow_user -d vinflow_production -h localhost
# Check .env file for correct credentials
```

#### 4. Celery Tasks Not Running

**Cause**: Redis not running or Celery worker down

**Solution**:
```bash
systemctl status redis
systemctl status vinflow-celery
redis-cli ping
journalctl -u vinflow-celery -n 50
```

#### 5. Permission Denied Errors

**Cause**: Wrong file ownership

**Solution**:
```bash
chown -R www-data:www-data /var/www/vinflow
chmod -R 755 /var/www/vinflow
chmod -R 775 /var/www/vinflow/media
```

### Debug Mode (Temporarily)

**Never run DEBUG=True in production permanently!**

For troubleshooting only:

```bash
# Edit .env
nano /var/www/vinflow/.env
# Change: DEBUG=True

# Restart services
systemctl restart vinflow-gunicorn

# Check issues, then IMMEDIATELY set back to False
# Change: DEBUG=False
systemctl restart vinflow-gunicorn
```

---

## Security Checklist

- [ ] Strong SECRET_KEY generated
- [ ] DEBUG=False in production
- [ ] Firewall configured (UFW)
- [ ] SSL certificate installed
- [ ] Database password is strong
- [ ] Only necessary ports open (80, 443, 22)
- [ ] SSH key authentication (disable password auth)
- [ ] Regular backups automated
- [ ] Fail2ban installed (optional but recommended)
- [ ] Keep system updated (apt update && apt upgrade)

---

## Performance Optimization

### 1. Enable Gzip Compression

Already configured in nginx.conf

### 2. Setup Redis Caching (Optional)

Add to `settings.py`:

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### 3. Database Connection Pooling

Install pgbouncer:

```bash
apt install pgbouncer -y
```

### 4. Monitor Performance

```bash
# Install monitoring tools
apt install vnstat iotop nethogs -y
```

---

## Additional Resources

- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Vultr Documentation](https://www.vultr.com/docs/)

---

## Support

For issues specific to VinFlow:
1. Check application logs
2. Review Django settings
3. Verify all services are running
4. Check firewall rules

For Vultr server issues:
- Visit Vultr support portal
- Check server dashboard

---

**Deployment completed! Your VinFlow application should now be live at https://your-domain.com** 🎉

