# VinFlow Deployment Files

This directory contains all the necessary configuration files and scripts for deploying VinFlow to a Vultr server.

## 📁 Files Overview

### Configuration Files

| File | Description | Usage |
|------|-------------|-------|
| `nginx.conf` | Nginx web server configuration | Copy to `/etc/nginx/sites-available/` |
| `gunicorn.service` | Systemd service for Gunicorn | Copy to `/etc/systemd/system/` |
| `celery.service` | Systemd service for Celery worker | Copy to `/etc/systemd/system/` |
| `celerybeat.service` | Systemd service for Celery Beat | Copy to `/etc/systemd/system/` |
| `env.production` | Production environment template | Copy to `.env` and configure |

### Scripts

| File | Description | Usage |
|------|-------------|-------|
| `deploy.sh` | Main deployment script | Run for updates |
| `backup.sh` | Database backup script | Run manually or via cron |
| `monitor.sh` | System health monitoring | Run via cron every 15 min |
| `update_requirements.sh` | Add missing packages to requirements | Run once |

### Documentation

| File | Description |
|------|-------------|
| `VULTR_DEPLOYMENT.md` | Complete deployment guide |
| `DEPLOYMENT_CHECKLIST.md` | Step-by-step checklist |
| `quick_reference.md` | Quick command reference |
| `crontab.example` | Example cron jobs |
| `README.md` | This file |

## 🚀 Quick Start

### First-Time Deployment

1. **Read the full guide**:
   ```bash
   cat deploy/VULTR_DEPLOYMENT.md
   ```

2. **Follow the checklist**:
   ```bash
   cat deploy/DEPLOYMENT_CHECKLIST.md
   ```

3. **Make scripts executable**:
   ```bash
   chmod +x deploy/*.sh
   ```

4. **Run initial setup** (follow VULTR_DEPLOYMENT.md steps)

### Updating Application

For code updates after initial deployment:

```bash
cd /var/www/vinflow
sudo ./deploy/deploy.sh
```

## 📋 Deployment Process Summary

1. **Server Setup**
   - Create Vultr VPS
   - Install dependencies (Python, PostgreSQL, Redis, Nginx)
   - Configure firewall

2. **Application Setup**
   - Clone repository
   - Create virtual environment
   - Install Python packages
   - Configure `.env` file

3. **Database Setup**
   - Create PostgreSQL database
   - Run migrations
   - Create superuser

4. **Web Server Setup**
   - Configure Nginx
   - Setup SSL with Let's Encrypt
   - Configure systemd services

5. **Deploy & Test**
   - Start all services
   - Test application
   - Setup monitoring and backups

## 🔧 Configuration Required

Before deploying, you MUST update:

### In `env.production`:
- `SECRET_KEY` - Generate a new one
- `ALLOWED_HOSTS` - Your domain and IP
- `DB_PASSWORD` - Strong database password
- Payment gateway credentials (PayPal, Stripe, KHQR)
- Domain URLs in all callback URLs

### In `nginx.conf`:
- Replace `your-domain.com` with actual domain
- Update SSL certificate paths after running Certbot

### In `deploy.sh`:
- Update `GIT_REPO` with your repository URL

### In `monitor.sh` & `backup.sh`:
- Update email addresses for alerts

## 📊 Service Architecture

```
┌─────────────┐
│   Nginx     │ :80, :443 (HTTPS)
│  (Reverse   │
│   Proxy)    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Gunicorn   │ :8000
│  (WSGI)     │
│  Workers    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Django    │
│ Application │
└──────┬──────┘
       │
       ├────────────┐
       ▼            ▼
┌──────────┐  ┌──────────┐
│PostgreSQL│  │  Redis   │
│ Database │  │  Cache   │
└──────────┘  └────┬─────┘
                   │
                   ▼
              ┌──────────┐
              │  Celery  │
              │  Workers │
              └──────────┘
```

## 🔐 Security Checklist

- ✅ DEBUG mode disabled in production
- ✅ Strong SECRET_KEY generated
- ✅ HTTPS enabled with valid SSL certificate
- ✅ Firewall configured (UFW)
- ✅ Database password is strong
- ✅ Security headers enabled in Nginx
- ✅ Django security middleware enabled
- ✅ CSRF and XSS protection enabled
- ✅ `.env` file not publicly accessible
- ✅ Regular backups configured

## 📁 Directory Structure on Server

```
/var/www/vinflow/
├── core/                    # Django project
├── panel/                   # Main app
├── templates/               # HTML templates
├── static/                  # Source static files
├── staticfiles/             # Collected static (served by Nginx)
├── media/                   # User uploads (served by Nginx)
├── venv/                    # Python virtual environment
├── .env                     # Environment variables
├── manage.py
├── requirements.txt
└── deploy/                  # Deployment files (this directory)

/var/log/vinflow/
├── gunicorn-access.log
├── gunicorn-error.log
├── celery-worker.log
└── celery-beat.log

/var/backups/vinflow/
└── backup_YYYYMMDD_HHMMSS.sql.gz

/etc/nginx/sites-available/
└── vinflow

/etc/systemd/system/
├── vinflow-gunicorn.service
├── vinflow-celery.service
└── vinflow-celerybeat.service
```

## 🔄 Update Workflow

1. Make changes to code locally
2. Commit and push to repository
3. SSH into server
4. Run deployment script:
   ```bash
   cd /var/www/vinflow
   sudo ./deploy/deploy.sh
   ```
5. Script will:
   - Pull latest code
   - Install dependencies
   - Run migrations
   - Collect static files
   - Restart services
   - Verify deployment

## 🔍 Monitoring

### Check Service Status
```bash
systemctl status vinflow-gunicorn
systemctl status vinflow-celery
systemctl status vinflow-celerybeat
```

### View Logs
```bash
tail -f /var/log/vinflow/gunicorn-error.log
tail -f /var/log/nginx/vinflow-error.log
journalctl -u vinflow-gunicorn -f
```

### Run Health Check
```bash
./deploy/monitor.sh
```

## 🆘 Troubleshooting

### 502 Bad Gateway
```bash
systemctl restart vinflow-gunicorn
journalctl -u vinflow-gunicorn -n 50
```

### Static Files Not Loading
```bash
python manage.py collectstatic --noinput
systemctl restart nginx
```

### Database Connection Error
```bash
systemctl status postgresql
# Check .env credentials
```

See `quick_reference.md` for more troubleshooting commands.

## 📞 Support

For detailed instructions, see:
- **Full Guide**: `VULTR_DEPLOYMENT.md`
- **Checklist**: `DEPLOYMENT_CHECKLIST.md`
- **Quick Ref**: `quick_reference.md`

## 📝 Notes

- Always test in a staging environment first
- Keep backups before major updates
- Monitor logs regularly
- Keep SSL certificates renewed (automatic with Certbot)
- Update system packages regularly
- Review security settings periodically

---

**Last Updated**: December 2025  
**Maintained By**: VinFlow Team

