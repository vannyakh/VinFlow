# VinFlow Deployment Guide for aaPanel

Complete step-by-step guide to deploy the VinFlow Django application on aaPanel.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [aaPanel Installation](#aapanel-installation)
3. [Initial Server Setup](#initial-server-setup)
4. [Installing Required Software](#installing-required-software)
5. [Setting Up the Database](#setting-up-the-database)
6. [Creating Python Project](#creating-python-project)
7. [Cloning the Repository](#cloning-the-repository)
8. [Configuring the Application](#configuring-the-application)
9. [Setting Up Redis](#setting-up-redis)
10. [Configuring Celery Workers](#configuring-celery-workers)
11. [Domain and SSL Setup](#domain-and-ssl-setup)
12. [Running the Deployment Script](#running-the-deployment-script)
13. [Post-Deployment Configuration](#post-deployment-configuration)
14. [Monitoring and Maintenance](#monitoring-and-maintenance)
15. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have:

- ✅ A VPS or dedicated server (minimum 2GB RAM, 2 CPU cores)
- ✅ Ubuntu 20.04 or 22.04 (recommended)
- ✅ Root or sudo access to the server
- ✅ Domain name (optional but recommended)
- ✅ SSH access to your server
- ✅ Basic knowledge of Linux commands

### Recommended Server Specifications

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 2GB | 4GB+ |
| CPU | 2 Cores | 4 Cores+ |
| Storage | 20GB | 50GB+ SSD |
| OS | Ubuntu 20.04 | Ubuntu 22.04 LTS |

---

## aaPanel Installation

### Step 1: Connect to Your Server

```bash
ssh root@your-server-ip
```

### Step 2: Update System Packages

```bash
apt update && apt upgrade -y
```

### Step 3: Install aaPanel

Run the official aaPanel installation script:

```bash
wget -O install.sh http://www.aapanel.com/script/install-ubuntu_6.0_en.sh && sudo bash install.sh aapanel
```

**Installation will take 5-10 minutes.**

### Step 4: Save aaPanel Credentials

After installation completes, you'll see output like:

```
==================================================================
Congratulations! Installed successfully!
==================================================================
aaPanel Internet Address: http://your-ip:7800/xxxxxxxx
aaPanel Internal Address: http://your-ip:7800/xxxxxxxx
username: xxxxxxxx
password: xxxxxxxx
==================================================================
```

**⚠️ IMPORTANT: Save these credentials immediately!**

### Step 5: Access aaPanel

1. Open your browser
2. Go to: `http://your-server-ip:7800/xxxxxxxx`
3. Login with the provided credentials
4. You'll be prompted to bind an aaPanel account (optional)

### Step 6: Recommended - Change Default Port

For security, change the default port:

1. Go to **Panel Settings** > **Panel Port**
2. Change from `7800` to a custom port (e.g., `8888`)
3. Update firewall rules if needed

---

## Initial Server Setup

### Step 1: Configure Firewall

In aaPanel Dashboard:

1. Go to **Security** tab
2. Add the following ports:

| Port | Protocol | Description |
|------|----------|-------------|
| 22 | TCP | SSH |
| 80 | TCP | HTTP |
| 443 | TCP | HTTPS |
| 7800 | TCP | aaPanel (or your custom port) |

### Step 2: Set Timezone

```bash
timedatectl set-timezone Asia/Phnom_Penh  # Change to your timezone
```

### Step 3: Create Swap Space (if needed)

For servers with limited RAM:

```bash
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' | tee -a /etc/fstab
```

---

## Installing Required Software

### Step 1: Install Software Stack

In aaPanel Dashboard, go to **App Store**:

1. **Nginx** - Click "Install" (recommended: latest stable version)
2. **Python Manager** - Click "Install"
3. **Database** - Choose one:
   - **MySQL 5.7** or **8.0** (recommended for production)
   - **PostgreSQL** (if preferred)
4. **Redis** - Click "Install" (required for caching and Celery)
5. **Supervisor** - Click "Install" (for managing processes)

Wait for all installations to complete (10-20 minutes).

### Step 2: Install Python 3.10+

1. Go to **App Store** > **Python Manager**
2. Install Python 3.10 or 3.11
3. Wait for installation to complete

### Step 3: Install Additional System Packages

Via SSH, install required system packages:

```bash
apt install -y git gettext libpq-dev python3-dev build-essential
```

---

## Setting Up the Database

### Option A: MySQL Setup

#### 1. Create Database via aaPanel

1. Go to **Database** tab
2. Click **Add Database**
3. Fill in:
   - **Database Name**: `vinflow_db`
   - **Username**: `vinflow_user`
   - **Password**: Generate a strong password
   - **Access Permission**: Select "localhost" or specific IP
4. Click **Submit**

#### 2. Save Credentials

Note down:
- Database name: `vinflow_db`
- Username: `vinflow_user`
- Password: `[your-generated-password]`
- Host: `localhost` or `127.0.0.1`

### Option B: PostgreSQL Setup

#### 1. Create Database via Terminal

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE vinflow_db;
CREATE USER vinflow_user WITH PASSWORD 'your-strong-password';
ALTER ROLE vinflow_user SET client_encoding TO 'utf8';
ALTER ROLE vinflow_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE vinflow_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE vinflow_db TO vinflow_user;
\q
```

---

## Creating Python Project

### Step 1: Create Project Directory

Via SSH:

```bash
mkdir -p /www/wwwroot/vinflow
cd /www/wwwroot/vinflow
```

### Step 2: Add Python Project in aaPanel

1. Go to **Website** tab
2. Click **Python Project**
3. Click **Add Python Project**
4. Fill in the form:

| Field | Value |
|-------|-------|
| **Project Name** | vinflow |
| **Project Path** | /www/wwwroot/vinflow |
| **Python Version** | 3.10 or 3.11 |
| **Framework** | Django |
| **Port** | 8000 (or any available port) |
| **Run Command** | (Leave empty for now) |

5. Click **Submit**

### Step 3: Configure Project Settings

After creation, click **Settings** on your project:

1. **Startup File**: Set to `gunicorn_config.py`
2. **Run Directory**: `/www/wwwroot/vinflow`
3. **Command**: 
   ```
   gunicorn core.wsgi:application -c gunicorn_config.py
   ```
4. **Auto Start**: Enable
5. Click **Save**

---

## Cloning the Repository

### Step 1: Clone Repository

```bash
cd /www/wwwroot
git clone https://github.com/vannyakh/vinflow.git vinflow
cd vinflow
```

If you already created the directory, clone into current directory:

```bash
cd /www/wwwroot/vinflow
git clone https://github.com/vannyakh/vinflow.git .
```

### Step 2: Set Proper Permissions

```bash
chown -R www:www /www/wwwroot/vinflow
chmod -R 755 /www/wwwroot/vinflow
```

---

## Configuring the Application

### Step 1: Create Virtual Environment

```bash
cd /www/wwwroot/vinflow
python3.10 -m venv venv
source venv/bin/activate
```

### Step 2: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

If you encounter any errors, install missing system packages:

```bash
apt install -y python3-dev libpq-dev gcc
```

### Step 3: Create .env File

Create environment configuration:

```bash
nano /www/wwwroot/vinflow/.env
```

Add the following configuration (adjust values):

```env
# Django Settings
SECRET_KEY=your-secret-key-here-generate-a-long-random-string
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-server-ip

# Database Configuration (MySQL)
DB_ENGINE=django.db.backends.mysql
DB_NAME=vinflow_db
DB_USER=vinflow_user
DB_PASSWORD=your-database-password
DB_HOST=localhost
DB_PORT=3306

# OR for PostgreSQL
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=vinflow_db
# DB_USER=vinflow_user
# DB_PASSWORD=your-database-password
# DB_HOST=localhost
# DB_PORT=5432

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email Configuration (Optional)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Payment Gateway Configuration
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=
PAYPAL_MODE=sandbox

# Stripe Configuration
STRIPE_PUBLIC_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Site Configuration
SITE_URL=https://your-domain.com
SITE_NAME=VinFlow

# Language
LANGUAGE_CODE=en-us
TIME_ZONE=Asia/Phnom_Penh
```

**Save and exit** (Ctrl+X, then Y, then Enter)

### Step 4: Generate Django Secret Key

Generate a secure secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output and update `SECRET_KEY` in your `.env` file.

### Step 5: Create Required Directories

```bash
mkdir -p /www/wwwroot/vinflow/{media,static,logs,backups}
chmod -R 775 /www/wwwroot/vinflow/{media,logs,backups}
```

### Step 6: Run Database Migrations

```bash
cd /www/wwwroot/vinflow
source venv/bin/activate
python manage.py migrate
```

### Step 7: Create Superuser

```bash
python manage.py createsuperuser
```

Follow the prompts to create an admin account.

### Step 8: Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### Step 9: Compile Translation Messages

```bash
python manage.py compilemessages
```

---

## Setting Up Redis

Redis should already be installed from the App Store.

### Step 1: Verify Redis is Running

```bash
redis-cli ping
```

Expected output: `PONG`

### Step 2: Configure Redis (Optional)

Edit Redis configuration if needed:

```bash
nano /www/server/redis/redis.conf
```

Recommended settings:

```conf
maxmemory 256mb
maxmemory-policy allkeys-lru
```

Restart Redis:

```bash
systemctl restart redis
```

---

## Configuring Celery Workers

### Step 1: Create Celery Service Files

#### Celery Worker Service

```bash
nano /etc/systemd/system/vinflow-celery.service
```

Add:

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
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Celery Beat Service

```bash
nano /etc/systemd/system/vinflow-celerybeat.service
```

Add:

```ini
[Unit]
Description=VinFlow Celery Beat
After=network.target redis.service

[Service]
Type=simple
User=www
Group=www
WorkingDirectory=/www/wwwroot/vinflow
Environment="PATH=/www/wwwroot/vinflow/venv/bin"
ExecStart=/www/wwwroot/vinflow/venv/bin/celery -A core beat --loglevel=info --logfile=/www/wwwroot/vinflow/logs/celerybeat.log --pidfile=/www/wwwroot/vinflow/celerybeat.pid
Restart=always

[Install]
WantedBy=multi-user.target
```

### Step 2: Enable and Start Services

```bash
systemctl daemon-reload
systemctl enable vinflow-celery vinflow-celerybeat
systemctl start vinflow-celery vinflow-celerybeat
```

### Step 3: Check Service Status

```bash
systemctl status vinflow-celery
systemctl status vinflow-celerybeat
```

---

## Domain and SSL Setup

### Step 1: Add Domain to aaPanel

1. Go to **Website** tab
2. Click **Add Site**
3. Fill in:
   - **Domain**: `your-domain.com,www.your-domain.com`
   - **Root Directory**: `/www/wwwroot/vinflow`
   - **PHP Version**: Select "Pure Static"
   - **Database**: Not needed (already created)
4. Click **Submit**

### Step 2: Configure Domain DNS

In your domain registrar (e.g., Cloudflare, GoDaddy):

Add these DNS records:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | your-server-ip | Auto |
| A | www | your-server-ip | Auto |

Wait for DNS propagation (5-30 minutes).

### Step 3: Configure Nginx for Django

1. In aaPanel, go to **Website** > Your Domain > **Settings**
2. Click **Config File**
3. Replace the content with:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name your-domain.com www.your-domain.com;
    
    # Redirect to HTTPS (will be configured later)
    # return 301 https://$server_name$request_uri;
    
    client_max_body_size 100M;
    
    # Static files
    location /static/ {
        alias /www/wwwroot/vinflow/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /www/wwwroot/vinflow/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # Proxy to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    # Access logs
    access_log /www/wwwlogs/vinflow.log;
    error_log /www/wwwlogs/vinflow.error.log;
}
```

4. Click **Save**

### Step 4: Install SSL Certificate

#### Option A: Let's Encrypt (Free, Recommended)

1. In your site settings, click **SSL**
2. Click **Let's Encrypt**
3. Check all domain variants
4. Click **Apply**
5. Wait for certificate to be issued

#### Option B: Upload Existing Certificate

1. Click **Other Certificate**
2. Paste your certificate and private key
3. Click **Save**

### Step 5: Enable HTTPS Redirect

After SSL is installed:

1. Go to **SSL** settings
2. Enable **Force HTTPS**

Or manually update Nginx config to uncomment the redirect line.

---

## Running the Deployment Script

### Step 1: Make Script Executable

```bash
chmod +x /www/wwwroot/vinflow/deploy/deploy.sh
```

### Step 2: Run Initial Deployment

```bash
cd /www/wwwroot/vinflow/deploy
./deploy.sh
```

The script will:
- ✅ Create database backup
- ✅ Pull latest code from Git
- ✅ Install/update dependencies
- ✅ Run migrations
- ✅ Compile translations
- ✅ Collect static files
- ✅ Set proper permissions
- ✅ Restart application

### Step 3: Verify Deployment

Check the output for any errors. If successful, you should see:

```
═══════════════════════════════════════════
Deployment completed successfully! 🎉
═══════════════════════════════════════════
```

---

## Post-Deployment Configuration

### Step 1: Access Admin Panel

Visit: `https://your-domain.com/admin/`

Login with the superuser credentials you created earlier.

### Step 2: Configure Site Settings

1. Go to **System Settings**
2. Update:
   - Site name
   - Logo
   - Contact information
   - Payment gateway credentials

### Step 3: Add Social Networks

1. Go to **Social Networks** section
2. Add your social media platforms and services

### Step 4: Create Services

1. Go to **Services** section
2. Add service categories
3. Add services with pricing

### Step 5: Configure Payment Methods

1. Go to **Payment Methods** section
2. Enable and configure:
   - PayPal
   - Stripe
   - KHQR/Bakong
   - Other methods

### Step 6: Test the Application

1. Register a test user
2. Place a test order
3. Test payment processing
4. Verify email notifications

---

## Monitoring and Maintenance

### Log Files

Important log locations:

| Log Type | Location |
|----------|----------|
| Application | `/www/wwwroot/vinflow/logs/` |
| Nginx Access | `/www/wwwlogs/vinflow.log` |
| Nginx Error | `/www/wwwlogs/vinflow.error.log` |
| Celery | `/www/wwwroot/vinflow/logs/celery.log` |
| Celery Beat | `/www/wwwroot/vinflow/logs/celerybeat.log` |

### View Logs

```bash
# Application logs
tail -f /www/wwwroot/vinflow/logs/*.log

# Nginx logs
tail -f /www/wwwlogs/vinflow*.log

# Celery logs
tail -f /www/wwwroot/vinflow/logs/celery.log
```

### Monitor Resources

In aaPanel Dashboard:
- Check CPU usage
- Check Memory usage
- Check Disk space
- Check Database size

### Automated Backups

#### Setup Cron Job for Daily Backups

```bash
crontab -e
```

Add:

```cron
# Daily database backup at 2 AM
0 2 * * * /www/wwwroot/vinflow/deploy/backup.sh

# Weekly full backup
0 3 * * 0 tar -czf /www/backup/vinflow_$(date +\%Y\%m\%d).tar.gz /www/wwwroot/vinflow
```

### Regular Maintenance Tasks

**Weekly:**
- Review log files
- Check disk space
- Monitor error rates
- Review security logs

**Monthly:**
- Update system packages
- Review and optimize database
- Check backup integrity
- Update SSL certificates (if manual)

**As Needed:**
- Update application code
- Update Python dependencies
- Apply security patches

---

## Troubleshooting

### Issue 1: Application Not Starting

**Check Gunicorn status:**

```bash
ps aux | grep gunicorn
```

**Restart application in aaPanel:**

1. Go to **Website** > **Python Project**
2. Find your project
3. Click **Restart**

**Check logs:**

```bash
tail -f /www/wwwlogs/vinflow.error.log
```

### Issue 2: Database Connection Errors

**Verify database credentials in .env:**

```bash
cat /www/wwwroot/vinflow/.env | grep DB_
```

**Test database connection:**

```bash
# For MySQL
mysql -u vinflow_user -p vinflow_db

# For PostgreSQL
psql -U vinflow_user -d vinflow_db
```

**Check database service:**

```bash
systemctl status mysql
# or
systemctl status postgresql
```

### Issue 3: Static Files Not Loading

**Collect static files again:**

```bash
cd /www/wwwroot/vinflow
source venv/bin/activate
python manage.py collectstatic --noinput
```

**Check permissions:**

```bash
chmod -R 755 /www/wwwroot/vinflow/staticfiles
chown -R www:www /www/wwwroot/vinflow/staticfiles
```

**Verify Nginx configuration:**

Check that static file location is correct in Nginx config.

### Issue 4: Celery Workers Not Running

**Check service status:**

```bash
systemctl status vinflow-celery
systemctl status vinflow-celerybeat
```

**View logs:**

```bash
tail -f /www/wwwroot/vinflow/logs/celery.log
```

**Restart services:**

```bash
systemctl restart vinflow-celery vinflow-celerybeat
```

### Issue 5: Permission Denied Errors

**Fix all permissions:**

```bash
chown -R www:www /www/wwwroot/vinflow
chmod -R 755 /www/wwwroot/vinflow
chmod -R 775 /www/wwwroot/vinflow/media
chmod -R 775 /www/wwwroot/vinflow/logs
```

### Issue 6: Redis Connection Errors

**Check Redis status:**

```bash
systemctl status redis
redis-cli ping
```

**Restart Redis:**

```bash
systemctl restart redis
```

### Issue 7: SSL Certificate Issues

**Renew Let's Encrypt certificate:**

In aaPanel:
1. Go to your site's **SSL** settings
2. Click **Renew**

**Check certificate expiry:**

```bash
echo | openssl s_client -servername your-domain.com -connect your-domain.com:443 2>/dev/null | openssl x509 -noout -dates
```

### Issue 8: High Memory Usage

**Check memory usage:**

```bash
free -h
htop
```

**Optimize Gunicorn workers:**

Edit `/www/wwwroot/vinflow/gunicorn_config.py`:

```python
# Reduce workers if memory is limited
workers = 2  # Instead of 4
```

**Restart application after changes.**

### Issue 9: Slow Performance

**Enable caching:**

Ensure Redis is properly configured in `settings.py`.

**Optimize database:**

```bash
# For MySQL
mysqlcheck -u root -p --optimize --all-databases

# For PostgreSQL
psql -U postgres -c "VACUUM ANALYZE;"
```

**Review Nginx caching:**

Add browser caching headers in Nginx config.

### Issue 10: Git Pull Errors

**Reset local changes:**

```bash
cd /www/wwwroot/vinflow
git stash
git pull origin main
```

**Or force reset:**

```bash
git fetch origin main
git reset --hard origin/main
```

---

## Useful Commands

### Application Management

```bash
# Restart application
pkill -f "gunicorn.*vinflow"

# View running processes
ps aux | grep vinflow

# Check port usage
netstat -tulpn | grep :8000
```

### Database Management

```bash
# Enter MySQL
mysql -u vinflow_user -p vinflow_db

# Backup database manually
mysqldump -u vinflow_user -p vinflow_db > backup.sql

# Restore database
mysql -u vinflow_user -p vinflow_db < backup.sql
```

### Log Management

```bash
# View recent errors
tail -100 /www/wwwlogs/vinflow.error.log

# Search for specific error
grep "ERROR" /www/wwwroot/vinflow/logs/*.log

# Clear old logs (keep last 7 days)
find /www/wwwroot/vinflow/logs -name "*.log" -mtime +7 -delete
```

### Updates and Maintenance

```bash
# Update system packages
apt update && apt upgrade -y

# Update Python packages
source /www/wwwroot/vinflow/venv/bin/activate
pip install --upgrade -r requirements.txt

# Run deployment script
cd /www/wwwroot/vinflow/deploy
./deploy.sh
```

---

## Security Best Practices

### 1. Change Default Passwords

- ✅ Change aaPanel admin password
- ✅ Use strong database passwords
- ✅ Generate unique Django SECRET_KEY

### 2. Configure Firewall

Only allow necessary ports:

```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 7800/tcp  # aaPanel port
ufw enable
```

### 3. Regular Updates

```bash
# Update system weekly
apt update && apt upgrade -y

# Update aaPanel
bt update
```

### 4. Enable Fail2ban

```bash
apt install -y fail2ban
systemctl enable fail2ban
systemctl start fail2ban
```

### 5. Backup Strategy

- Daily database backups
- Weekly full application backups
- Store backups off-site
- Test restore procedures regularly

### 6. Monitor Security

- Review access logs daily
- Set up alerts for failed login attempts
- Monitor for unusual traffic patterns
- Keep SSL certificates up to date

---

## Support and Resources

### Documentation

- Django Documentation: https://docs.djangoproject.com/
- aaPanel Documentation: https://www.aapanel.com/reference.html
- Nginx Documentation: https://nginx.org/en/docs/

### Getting Help

If you encounter issues:

1. Check the logs first
2. Review this documentation
3. Search for error messages online
4. Contact your system administrator
5. Open an issue on the project repository

---

## Conclusion

You have successfully deployed VinFlow on aaPanel! 🎉

Your application is now:
- ✅ Running on production server
- ✅ Secured with SSL
- ✅ Backed up automatically
- ✅ Monitored and maintained

### Next Steps

1. Configure all payment gateways
2. Add your services and pricing
3. Test all features thoroughly
4. Announce your launch
5. Monitor performance and user feedback

---

## Appendix

### A. Environment Variables Reference

Complete list of available environment variables:

```env
# Required
SECRET_KEY=
DEBUG=
ALLOWED_HOSTS=
DB_ENGINE=
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=

# Redis/Celery
REDIS_HOST=
REDIS_PORT=
CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=

# Email
EMAIL_BACKEND=
EMAIL_HOST=
EMAIL_PORT=
EMAIL_USE_TLS=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

# Payments
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=
PAYPAL_MODE=
STRIPE_PUBLIC_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Site
SITE_URL=
SITE_NAME=
LANGUAGE_CODE=
TIME_ZONE=
```

### B. File Structure

```
/www/wwwroot/vinflow/
├── core/                 # Django core settings
├── panel/                # Main application
├── static/               # Static assets
├── staticfiles/          # Collected static files
├── media/                # User uploads
├── locale/               # Translations
├── templates/            # HTML templates
├── deploy/               # Deployment scripts
├── docs/                 # Documentation
├── logs/                 # Application logs
├── backups/              # Database backups
├── venv/                 # Virtual environment
├── manage.py            # Django management script
├── requirements.txt      # Python dependencies
├── gunicorn_config.py   # Gunicorn configuration
└── .env                 # Environment variables
```

### C. Port Reference

| Service | Default Port | Description |
|---------|-------------|-------------|
| aaPanel | 7800 | Web interface |
| HTTP | 80 | Web traffic |
| HTTPS | 443 | Secure web traffic |
| SSH | 22 | Remote access |
| Gunicorn | 8000 | Application server |
| MySQL | 3306 | Database |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache/Queue |

---

**Document Version:** 1.0  
**Last Updated:** December 2025  
**Author:** VinFlow Team

---

For questions or support, please contact your system administrator or open an issue on the project repository.

