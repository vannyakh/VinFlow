# VinFlow Deployment Checklist

Use this checklist to ensure a smooth deployment to your Vultr server.

## Pre-Deployment

### 1. Server Preparation
- [ ] Vultr VPS created (Ubuntu 22.04/24.04 LTS)
- [ ] Domain name configured and DNS pointing to server IP
- [ ] SSH access configured
- [ ] Server updated: `apt update && apt upgrade -y`
- [ ] Firewall configured (UFW)
- [ ] Non-root user created (optional but recommended)

### 2. Software Installation
- [ ] Python 3.10+ installed
- [ ] PostgreSQL 14+ installed and running
- [ ] Redis installed and running
- [ ] Nginx installed
- [ ] Git installed
- [ ] Build tools installed (`build-essential`, `libpq-dev`)

### 3. Database Setup
- [ ] PostgreSQL database created
- [ ] Database user created with proper privileges
- [ ] Database connection tested
- [ ] Strong database password set

### 4. Application Files
- [ ] Code repository cloned or uploaded to `/var/www/vinflow`
- [ ] Virtual environment created
- [ ] Python dependencies installed
- [ ] Gunicorn installed

### 5. Environment Configuration
- [ ] `.env` file created from `deploy/env.production`
- [ ] Strong `SECRET_KEY` generated
- [ ] `DEBUG=False` set
- [ ] `ALLOWED_HOSTS` configured with domain and IP
- [ ] Database credentials updated
- [ ] Payment gateway credentials updated (PayPal, Stripe, KHQR)
- [ ] Redis connection string updated
- [ ] All callback URLs updated to production domain

## Deployment Steps

### 6. Django Setup
- [ ] Migrations applied: `python manage.py migrate`
- [ ] Superuser created: `python manage.py createsuperuser`
- [ ] Static files collected: `python manage.py collectstatic`
- [ ] Translation messages compiled: `python manage.py compilemessages`
- [ ] Initial settings initialized: `python manage.py init_default_settings`

### 7. File Permissions
- [ ] Log directory created: `/var/log/vinflow`
- [ ] Run directory created: `/var/run/vinflow`
- [ ] Correct ownership set: `chown -R www-data:www-data /var/www/vinflow`
- [ ] Correct permissions set: `chmod -R 755 /var/www/vinflow`
- [ ] Media directory writable: `chmod -R 775 /var/www/vinflow/media`
- [ ] Log directory writable: `chown -R www-data:www-data /var/log/vinflow`

### 8. Nginx Configuration
- [ ] Nginx config copied to `/etc/nginx/sites-available/vinflow`
- [ ] Domain name updated in nginx config
- [ ] Symlink created in `/etc/nginx/sites-enabled/`
- [ ] Default site removed
- [ ] Nginx configuration tested: `nginx -t`
- [ ] Nginx reloaded: `systemctl reload nginx`

### 9. SSL Certificate
- [ ] Certbot installed
- [ ] SSL certificate obtained: `certbot --nginx -d your-domain.com`
- [ ] Auto-renewal tested: `certbot renew --dry-run`
- [ ] HTTPS redirect verified
- [ ] Certificate paths updated in nginx config

### 10. Systemd Services
- [ ] Gunicorn service file copied to `/etc/systemd/system/vinflow-gunicorn.service`
- [ ] Celery service file copied to `/etc/systemd/system/vinflow-celery.service`
- [ ] Celery Beat service file copied to `/etc/systemd/system/vinflow-celerybeat.service`
- [ ] Service files reviewed and paths updated if needed
- [ ] Systemd daemon reloaded: `systemctl daemon-reload`
- [ ] Gunicorn service started: `systemctl start vinflow-gunicorn`
- [ ] Celery service started: `systemctl start vinflow-celery`
- [ ] Celery Beat service started: `systemctl start vinflow-celerybeat`
- [ ] All services enabled on boot:
  - `systemctl enable vinflow-gunicorn`
  - `systemctl enable vinflow-celery`
  - `systemctl enable vinflow-celerybeat`

### 11. Service Verification
- [ ] Gunicorn running: `systemctl status vinflow-gunicorn`
- [ ] Celery worker running: `systemctl status vinflow-celery`
- [ ] Celery Beat running: `systemctl status vinflow-celerybeat`
- [ ] Nginx running: `systemctl status nginx`
- [ ] Redis running: `systemctl status redis`
- [ ] PostgreSQL running: `systemctl status postgresql`

## Post-Deployment Testing

### 12. Application Testing
- [ ] Website accessible via HTTPS
- [ ] Homepage loads correctly
- [ ] Login functionality works
- [ ] Admin panel accessible
- [ ] Static files loading (CSS, JS, images)
- [ ] Media files accessible
- [ ] User registration works
- [ ] Order creation works
- [ ] Payment gateways responding (test mode)
- [ ] Language switcher works (EN/KM)
- [ ] 2FA setup works
- [ ] API endpoints responding
- [ ] Mobile view works properly

### 13. Security Verification
- [ ] HTTP redirects to HTTPS
- [ ] SSL certificate valid (check on ssllabs.com)
- [ ] Security headers present (check on securityheaders.com)
- [ ] Debug mode disabled (`DEBUG=False`)
- [ ] Admin panel only accessible with authentication
- [ ] Database credentials not exposed
- [ ] `.env` file not publicly accessible
- [ ] Error pages show generic messages (not debug info)

### 14. Performance Check
- [ ] Page load times acceptable
- [ ] Static files cached properly
- [ ] Gzip compression enabled
- [ ] Database queries optimized
- [ ] Celery tasks processing
- [ ] Redis responding quickly

### 15. Monitoring Setup
- [ ] Log files being created
- [ ] Log rotation configured
- [ ] Gunicorn access logs: `/var/log/vinflow/gunicorn-access.log`
- [ ] Gunicorn error logs: `/var/log/vinflow/gunicorn-error.log`
- [ ] Nginx access logs: `/var/log/nginx/vinflow-access.log`
- [ ] Nginx error logs: `/var/log/nginx/vinflow-error.log`
- [ ] Celery logs: `/var/log/vinflow/celery-worker.log`

### 16. Backup Configuration
- [ ] Backup script configured: `deploy/backup.sh`
- [ ] Backup script executable: `chmod +x deploy/backup.sh`
- [ ] Test backup run: `./deploy/backup.sh`
- [ ] Backup directory exists: `/var/backups/vinflow`
- [ ] Cron job added for daily backups
- [ ] Backup retention policy set (30 days)
- [ ] Test backup restoration

### 17. Automation Setup
- [ ] Deployment script executable: `chmod +x deploy/deploy.sh`
- [ ] Monitor script executable: `chmod +x deploy/monitor.sh`
- [ ] Crontab configured with tasks:
  - [ ] Daily database backup
  - [ ] System health monitoring
  - [ ] Weekly session cleanup
  - [ ] Monthly database VACUUM
- [ ] Email alerts configured (optional)

## Production Checklist

### 18. Payment Gateways (Production)
- [ ] PayPal switched to live mode
- [ ] PayPal production credentials configured
- [ ] Stripe production keys configured
- [ ] Stripe webhook configured and tested
- [ ] KHQR production credentials configured
- [ ] All payment callbacks using HTTPS
- [ ] Test transactions completed successfully

### 19. Final Configuration
- [ ] Google OAuth production credentials
- [ ] Email SMTP configured (for notifications)
- [ ] SMS gateway configured (if applicable)
- [ ] Analytics tracking added (Google Analytics, etc.)
- [ ] SEO meta tags configured
- [ ] Robots.txt configured
- [ ] Sitemap generated
- [ ] Favicon set

### 20. Documentation
- [ ] Deployment notes documented
- [ ] Server access details stored securely
- [ ] Database credentials stored securely
- [ ] API keys stored securely (use password manager)
- [ ] Emergency contacts listed
- [ ] Backup restoration procedure documented

## Ongoing Maintenance

### 21. Regular Tasks
- [ ] Monitor server resources (daily)
- [ ] Check application logs (daily)
- [ ] Review failed celery tasks (daily)
- [ ] Backup verification (weekly)
- [ ] Security updates (weekly)
- [ ] Database optimization (monthly)
- [ ] SSL certificate renewal (automatic)
- [ ] Update Python packages (monthly)
- [ ] Update system packages (weekly)

### 22. Monitoring Alerts
- [ ] Disk space monitoring (alert at 85%)
- [ ] Memory usage monitoring
- [ ] Service uptime monitoring
- [ ] Database connection monitoring
- [ ] SSL certificate expiry monitoring
- [ ] Failed login attempts monitoring
- [ ] Error rate monitoring

## Rollback Plan

### 23. Emergency Procedures
- [ ] Previous version code tagged in git
- [ ] Database backup before deployment
- [ ] Rollback procedure documented
- [ ] Quick restore procedure tested
- [ ] Emergency contact list available
- [ ] Service restart commands documented

---

## Quick Commands Reference

### Deploy Update
```bash
cd /var/www/vinflow
sudo ./deploy/deploy.sh
```

### Check All Services
```bash
systemctl status vinflow-gunicorn vinflow-celery vinflow-celerybeat nginx redis postgresql
```

### View Logs
```bash
sudo tail -f /var/log/vinflow/gunicorn-error.log
sudo tail -f /var/log/nginx/vinflow-error.log
sudo journalctl -u vinflow-gunicorn -f
```

### Restart Services
```bash
sudo systemctl restart vinflow-gunicorn vinflow-celery vinflow-celerybeat nginx
```

---

## Sign-Off

**Deployment Date**: _______________

**Deployed By**: _______________

**Server IP**: _______________

**Domain**: _______________

**Database Name**: _______________

**All Checks Passed**: [ ] YES [ ] NO

**Production Ready**: [ ] YES [ ] NO

**Notes**:
```
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
```

---

## Support Resources

- **VinFlow Docs**: `/var/www/vinflow/docs/`
- **Django Docs**: https://docs.djangoproject.com/
- **Nginx Docs**: https://nginx.org/en/docs/
- **Vultr Docs**: https://www.vultr.com/docs/
- **Let's Encrypt**: https://letsencrypt.org/

---

**Remember**: Test thoroughly in a staging environment before deploying to production!

