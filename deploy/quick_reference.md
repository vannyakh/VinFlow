# VinFlow - Quick Deployment Reference

## Quick Commands

### Service Management

```bash
# Restart all services
sudo systemctl restart vinflow-gunicorn vinflow-celery vinflow-celerybeat nginx

# Check service status
sudo systemctl status vinflow-gunicorn
sudo systemctl status vinflow-celery
sudo systemctl status vinflow-celerybeat

# View live logs
sudo journalctl -u vinflow-gunicorn -f
sudo tail -f /var/log/vinflow/gunicorn-error.log
sudo tail -f /var/log/nginx/vinflow-error.log
```

### Deploy Updates

```bash
cd /var/www/vinflow
sudo ./deploy/deploy.sh
```

### Manual Deployment Steps

```bash
cd /var/www/vinflow
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py compilemessages
sudo systemctl restart vinflow-gunicorn vinflow-celery
```

### Database Operations

```bash
# Backup database
pg_dump -U vinflow_user -h localhost vinflow_production > backup.sql

# Restore database
psql -U vinflow_user -h localhost vinflow_production < backup.sql

# Access database
psql -U vinflow_user -h localhost vinflow_production
```

### Check Server Resources

```bash
# Memory usage
free -m

# Disk usage
df -h

# CPU usage
top
# or
htop

# Active connections
netstat -tuln | grep LISTEN
```

### SSL Certificate Renewal

```bash
# Renew certificate (automatic via cron)
sudo certbot renew

# Force renewal
sudo certbot renew --force-renewal

# Test renewal
sudo certbot renew --dry-run
```

### Nginx Commands

```bash
# Test configuration
sudo nginx -t

# Reload configuration
sudo systemctl reload nginx

# Restart nginx
sudo systemctl restart nginx

# View error logs
sudo tail -f /var/log/nginx/error.log
```

### Django Management

```bash
cd /var/www/vinflow
source venv/bin/activate

# Create superuser
python manage.py createsuperuser

# Shell access
python manage.py shell

# Check migrations
python manage.py showmigrations

# Create migration
python manage.py makemigrations

# Apply migrations
python manage.py migrate
```

### Redis Operations

```bash
# Connect to Redis CLI
redis-cli

# Check Redis status
sudo systemctl status redis

# Monitor Redis
redis-cli monitor

# Clear Redis cache
redis-cli FLUSHALL
```

### File Permissions

```bash
# Fix ownership
sudo chown -R www-data:www-data /var/www/vinflow

# Fix permissions
sudo chmod -R 755 /var/www/vinflow
sudo chmod -R 775 /var/www/vinflow/media

# Fix log permissions
sudo chown -R www-data:www-data /var/log/vinflow
```

### Monitoring

```bash
# Check running Python processes
ps aux | grep python

# Check Gunicorn workers
ps aux | grep gunicorn

# Check Celery workers
ps aux | grep celery

# Check disk I/O
sudo iotop

# Check network usage
sudo nethogs
```

### Troubleshooting

```bash
# Clear sessions
cd /var/www/vinflow
source venv/bin/activate
python manage.py clearsessions

# Restart all services fresh
sudo systemctl stop vinflow-gunicorn vinflow-celery vinflow-celerybeat
sudo systemctl start vinflow-gunicorn vinflow-celery vinflow-celerybeat
sudo systemctl restart nginx

# Check for port conflicts
sudo netstat -tulpn | grep :8000

# Kill stuck processes
sudo pkill -f gunicorn
sudo pkill -f celery
```

### Firewall Management

```bash
# Check firewall status
sudo ufw status

# Allow new port
sudo ufw allow 8080/tcp

# Deny port
sudo ufw deny 8080/tcp

# Reset firewall (careful!)
sudo ufw reset
```

### System Updates

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Update Python packages
cd /var/www/vinflow
source venv/bin/activate
pip list --outdated
pip install --upgrade package-name
```

---

## Important File Locations

- **Application**: `/var/www/vinflow`
- **Virtual Environment**: `/var/www/vinflow/venv`
- **Environment File**: `/var/www/vinflow/.env`
- **Static Files**: `/var/www/vinflow/staticfiles`
- **Media Files**: `/var/www/vinflow/media`
- **Logs**: `/var/log/vinflow/`
- **Nginx Config**: `/etc/nginx/sites-available/vinflow`
- **Systemd Services**: `/etc/systemd/system/vinflow-*.service`
- **SSL Certs**: `/etc/letsencrypt/live/your-domain.com/`

---

## Common Issues & Solutions

### 502 Bad Gateway
```bash
sudo systemctl restart vinflow-gunicorn
sudo journalctl -u vinflow-gunicorn -n 50
```

### Static files not loading
```bash
cd /var/www/vinflow
source venv/bin/activate
python manage.py collectstatic --noinput
sudo chown -R www-data:www-data staticfiles
sudo systemctl restart nginx
```

### Database connection error
```bash
sudo systemctl status postgresql
# Check .env file credentials
nano /var/www/vinflow/.env
```

### Out of memory
```bash
# Check memory
free -m
# Add swap space if needed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## Performance Tips

1. **Monitor logs regularly**: Set up log rotation
2. **Database optimization**: Run VACUUM on PostgreSQL monthly
3. **Clear old sessions**: Run `clearsessions` weekly
4. **Monitor disk space**: Keep at least 20% free
5. **Update regularly**: Keep packages up to date
6. **Backup daily**: Automate database backups

---

## Emergency Contacts

- Vultr Support: https://my.vultr.com/support/
- Django Docs: https://docs.djangoproject.com/
- Server IP: `your-server-ip`
- Domain: `your-domain.com`

