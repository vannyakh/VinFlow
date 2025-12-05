# VinFlow aaPanel - Quick Start Guide

Quick reference for deploying and managing VinFlow on aaPanel.

## 🚀 Quick Installation Steps

### 1. Install aaPanel (5 minutes)

```bash
wget -O install.sh http://www.aapanel.com/script/install-ubuntu_6.0_en.sh
sudo bash install.sh aapanel
```

Save the login credentials shown after installation!

### 2. Install Software Stack (15 minutes)

In aaPanel Dashboard → **App Store**, install:
- ✅ Nginx (latest)
- ✅ Python Manager (3.10+)
- ✅ MySQL 8.0 or PostgreSQL
- ✅ Redis
- ✅ Supervisor

### 3. Create Database (2 minutes)

**Database** tab → **Add Database**:
- Name: `vinflow_db`
- User: `vinflow_user`
- Password: [generate strong password]

### 4. Clone Repository (2 minutes)

```bash
cd /www/wwwroot
git clone https://github.com/vannyakh/vinflow.git vinflow
cd vinflow
```

### 5. Setup Environment (5 minutes)

```bash
# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
cp env.example .env
nano .env  # Edit with your settings
```

### 6. Configure Application (3 minutes)

```bash
# Create directories
mkdir -p media static logs backups

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### 7. Setup Python Project in aaPanel (2 minutes)

**Website** → **Python Project** → **Add Project**:
- Name: `vinflow`
- Path: `/www/wwwroot/vinflow`
- Python: `3.10`
- Port: `8000`
- Command: `gunicorn core.wsgi:application -c gunicorn_config.py`

### 8. Configure Domain & SSL (5 minutes)

**Website** → **Add Site**:
- Domain: `your-domain.com`
- Root: `/www/wwwroot/vinflow`

Then configure Nginx (see full manual) and enable SSL.

### 9. Setup Celery Workers (3 minutes)

```bash
# Create service files
sudo nano /etc/systemd/system/vinflow-celery.service
sudo nano /etc/systemd/system/vinflow-celerybeat.service

# Enable and start
sudo systemctl enable vinflow-celery vinflow-celerybeat
sudo systemctl start vinflow-celery vinflow-celerybeat
```

### 10. Deploy! (1 minute)

```bash
cd /www/wwwroot/vinflow/deploy
chmod +x deploy.sh
./deploy.sh
```

**Total Time: ~40 minutes** ⏱️

---

## 📋 Essential Commands

### Application Management

```bash
# Restart application
pkill -f "gunicorn.*vinflow"

# Check if running
ps aux | grep gunicorn

# View logs
tail -f /www/wwwlogs/vinflow.error.log
```

### Deployment

```bash
# Quick deploy
cd /www/wwwroot/vinflow/deploy
./deploy.sh

# Manual steps
cd /www/wwwroot/vinflow
source venv/bin/activate
git pull origin main
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

### Database

```bash
# Backup
mysqldump -u vinflow_user -p vinflow_db > backup.sql

# Restore
mysql -u vinflow_user -p vinflow_db < backup.sql

# Access
mysql -u vinflow_user -p vinflow_db
```

### Celery

```bash
# Restart workers
sudo systemctl restart vinflow-celery vinflow-celerybeat

# Check status
sudo systemctl status vinflow-celery

# View logs
tail -f /www/wwwroot/vinflow/logs/celery.log
```

### Permissions

```bash
# Fix all permissions
sudo chown -R www:www /www/wwwroot/vinflow
sudo chmod -R 755 /www/wwwroot/vinflow
sudo chmod -R 775 /www/wwwroot/vinflow/media
sudo chmod -R 775 /www/wwwroot/vinflow/logs
```

---

## ⚙️ Configuration Files

### .env Configuration

```env
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

DB_ENGINE=django.db.backends.mysql
DB_NAME=vinflow_db
DB_USER=vinflow_user
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=3306

REDIS_HOST=localhost
REDIS_PORT=6379

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

SITE_URL=https://your-domain.com
TIME_ZONE=Asia/Phnom_Penh
```

### Nginx Configuration Template

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    client_max_body_size 100M;
    
    location /static/ {
        alias /www/wwwroot/vinflow/staticfiles/;
        expires 30d;
    }
    
    location /media/ {
        alias /www/wwwroot/vinflow/media/;
        expires 7d;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Celery Service Template

```ini
[Unit]
Description=VinFlow Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=www
Group=www
WorkingDirectory=/www/wwwroot/vinflow
Environment="PATH=/www/wwwroot/vinflow/venv/bin"
ExecStart=/www/wwwroot/vinflow/venv/bin/celery -A core worker --loglevel=info --logfile=/www/wwwroot/vinflow/logs/celery.log --pidfile=/www/wwwroot/vinflow/celery.pid --detach
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 🔍 Quick Troubleshooting

### Application won't start

```bash
# Check logs
tail -f /www/wwwlogs/vinflow.error.log

# Check if port is in use
netstat -tulpn | grep :8000

# Restart in aaPanel
# Website → Python Project → Restart
```

### Database connection failed

```bash
# Test connection
mysql -u vinflow_user -p vinflow_db

# Check credentials in .env
cat /www/wwwroot/vinflow/.env | grep DB_

# Restart MySQL
sudo systemctl restart mysql
```

### Static files not loading

```bash
# Recollect
cd /www/wwwroot/vinflow
source venv/bin/activate
python manage.py collectstatic --noinput

# Fix permissions
sudo chmod -R 755 staticfiles/
```

### Celery not working

```bash
# Check Redis
redis-cli ping

# Restart services
sudo systemctl restart vinflow-celery vinflow-celerybeat

# Check logs
tail -f /www/wwwroot/vinflow/logs/celery.log
```

### Permission errors

```bash
# Fix ownership
sudo chown -R www:www /www/wwwroot/vinflow

# Fix permissions
sudo chmod -R 755 /www/wwwroot/vinflow
sudo chmod -R 775 /www/wwwroot/vinflow/{media,logs}
```

---

## 📊 Health Checks

### Quick System Check

```bash
# Check all services
sudo systemctl status nginx
sudo systemctl status mysql
sudo systemctl status redis
sudo systemctl status vinflow-celery
sudo systemctl status vinflow-celerybeat

# Check processes
ps aux | grep -E "gunicorn|celery|redis|mysql"

# Check disk space
df -h

# Check memory
free -h

# Check logs for errors
tail -100 /www/wwwlogs/vinflow.error.log | grep ERROR
```

### Application Health

```bash
cd /www/wwwroot/vinflow
source venv/bin/activate

# Run Django checks
python manage.py check

# Test database connection
python manage.py dbshell

# Check migrations
python manage.py showmigrations
```

---

## 🔒 Security Checklist

- [ ] Changed aaPanel default password
- [ ] Changed database passwords
- [ ] Generated new SECRET_KEY
- [ ] Set DEBUG=False
- [ ] Configured ALLOWED_HOSTS
- [ ] Enabled firewall (UFW)
- [ ] Installed SSL certificate
- [ ] Enabled HTTPS redirect
- [ ] Set proper file permissions
- [ ] Configured automated backups
- [ ] Installed Fail2ban
- [ ] Disabled root SSH login (optional)

---

## 📦 Daily Operations

### Morning Routine

```bash
# Check service status
systemctl status vinflow-celery vinflow-celerybeat

# Check last night's logs
grep ERROR /www/wwwroot/vinflow/logs/*.log

# Check disk space
df -h
```

### Deployment Routine

```bash
# 1. Backup first
cd /www/wwwroot/vinflow/deploy
./deploy.sh  # This includes backup

# 2. Or manual backup
mysqldump -u vinflow_user -p vinflow_db > backup_$(date +%Y%m%d).sql

# 3. Deploy
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
pkill -f "gunicorn.*vinflow"

# 4. Verify
curl -I https://your-domain.com
tail -f /www/wwwlogs/vinflow.error.log
```

### Weekly Maintenance

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Clean old logs (older than 30 days)
find /www/wwwroot/vinflow/logs -name "*.log" -mtime +30 -delete

# Clean old backups (keep last 10)
ls -t /www/wwwroot/vinflow/backups/*.gz | tail -n +11 | xargs rm -f

# Optimize database
mysql -u root -p -e "OPTIMIZE TABLE vinflow_db.*"

# Check SSL expiry
echo | openssl s_client -servername your-domain.com -connect your-domain.com:443 2>/dev/null | openssl x509 -noout -dates
```

---

## 🎯 Performance Tips

### Optimize Gunicorn

Edit `gunicorn_config.py`:

```python
# For 2GB RAM server
workers = 2
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 5
```

### Enable Redis Caching

In Django settings, ensure:

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### Optimize MySQL

```bash
mysql -u root -p

# Run these queries
OPTIMIZE TABLE panel_order;
OPTIMIZE TABLE panel_payment;
ANALYZE TABLE panel_service;
```

### Monitor Performance

```bash
# Check response time
curl -o /dev/null -s -w "Time: %{time_total}s\n" https://your-domain.com

# Check active connections
netstat -an | grep :8000 | wc -l

# Check memory by process
ps aux --sort=-%mem | head -10
```

---

## 📞 Quick Reference

### Important Paths

| Resource | Path |
|----------|------|
| Application | `/www/wwwroot/vinflow` |
| Logs | `/www/wwwroot/vinflow/logs/` |
| Nginx Logs | `/www/wwwlogs/` |
| Media Files | `/www/wwwroot/vinflow/media/` |
| Static Files | `/www/wwwroot/vinflow/staticfiles/` |
| Backups | `/www/wwwroot/vinflow/backups/` |
| Virtual Env | `/www/wwwroot/vinflow/venv/` |

### Important Ports

| Service | Port |
|---------|------|
| aaPanel | 7800 |
| HTTP | 80 |
| HTTPS | 443 |
| Gunicorn | 8000 |
| MySQL | 3306 |
| Redis | 6379 |

### Service Names

| Service | Systemd Name |
|---------|--------------|
| Celery Worker | `vinflow-celery` |
| Celery Beat | `vinflow-celerybeat` |
| MySQL | `mysql` |
| Redis | `redis` |
| Nginx | `nginx` |

---

## 🆘 Emergency Procedures

### Application Down

```bash
# 1. Check what's wrong
systemctl status nginx
ps aux | grep gunicorn

# 2. Restart everything
systemctl restart nginx
pkill -f "gunicorn.*vinflow"

# 3. Check logs
tail -f /www/wwwlogs/vinflow.error.log
```

### Database Down

```bash
# 1. Check status
systemctl status mysql

# 2. Restart
systemctl restart mysql

# 3. If won't start, check logs
tail -f /var/log/mysql/error.log
```

### Out of Disk Space

```bash
# 1. Check usage
df -h

# 2. Find large files
du -sh /www/wwwroot/vinflow/* | sort -rh | head -10

# 3. Clean up
# Remove old logs
find /www/wwwroot/vinflow/logs -name "*.log" -mtime +7 -delete

# Remove old backups
find /www/wwwroot/vinflow/backups -name "*.gz" -mtime +30 -delete

# Clean package cache
apt clean
```

### High Memory Usage

```bash
# 1. Check what's using memory
ps aux --sort=-%mem | head -10

# 2. Restart memory-heavy services
systemctl restart vinflow-celery
pkill -f "gunicorn.*vinflow"

# 3. If still high, add swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📚 Additional Resources

- **Full Manual**: `/www/wwwroot/vinflow/docs/AAPANEL_DEPLOYMENT.md`
- **Deploy Script**: `/www/wwwroot/vinflow/deploy/deploy.sh`
- **aaPanel Docs**: https://www.aapanel.com/reference.html
- **Django Docs**: https://docs.djangoproject.com/

---

**Quick Start Guide Version:** 1.0  
**Last Updated:** December 2025

For detailed instructions, refer to the full deployment manual.

