# Docker Quick Start Guide

## 🚀 Quick Setup (2 Minutes)

### Option 1: Automated Setup

```bash
# Run the setup script
./Docker/docker-setup.sh
```

### Option 2: Manual Setup

```bash
# 1. Create environment file
cp env.docker.example .env

# 2. Build and start
docker-compose -f Docker/docker-compose.yml up -d --build

# 3. Create superuser
docker-compose -f Docker/docker-compose.yml exec web python manage.py createsuperuser
```

## 📋 Essential Commands

### Start/Stop

```bash
# Start all services
docker-compose -f Docker/docker-compose.yml up -d

# Stop all services
docker-compose -f Docker/docker-compose.yml down

# Restart services
docker-compose -f Docker/docker-compose.yml restart

# View status
docker-compose -f Docker/docker-compose.yml ps
```

### Logs

```bash
# All services
docker-compose -f Docker/docker-compose.yml logs -f

# Specific service
docker-compose -f Docker/docker-compose.yml logs -f web
docker-compose -f Docker/docker-compose.yml logs -f celery_worker
```

### Django Commands

```bash
# Migrations
docker-compose -f Docker/docker-compose.yml exec web python manage.py migrate
docker-compose -f Docker/docker-compose.yml exec web python manage.py makemigrations

# Create superuser
docker-compose -f Docker/docker-compose.yml exec web python manage.py createsuperuser

# Django shell
docker-compose -f Docker/docker-compose.yml exec web python manage.py shell

# Collect static files
docker-compose -f Docker/docker-compose.yml exec web python manage.py collectstatic
```

### Database

```bash
# Access database
docker-compose -f Docker/docker-compose.yml exec db psql -U postgres -d vinflow_dev

# Backup
docker-compose -f Docker/docker-compose.yml exec db pg_dump -U postgres vinflow_dev > backup.sql

# Restore
docker-compose -f Docker/docker-compose.yml exec -T db psql -U postgres vinflow_dev < backup.sql
```

## 🎯 Using Makefile (Recommended)

```bash
# View all commands
make -f Makefile.docker help

# Common operations
make -f Makefile.docker up-build    # Build and start
make -f Makefile.docker logs        # View logs
make -f Makefile.docker shell       # Django shell
make -f Makefile.docker migrate     # Run migrations
make -f Makefile.docker down        # Stop services
```

## 🔧 Configuration

Edit `.env` file to configure:

- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode (True/False)
- `DB_PASSWORD` - Database password
- Payment gateway credentials
- Other settings

## 📍 Access Points

- **Application**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **Database**: localhost:5432
- **Redis**: localhost:6379

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Check what's using the port
lsof -i :8000

# Or change port in docker-compose.yml
ports:
  - "8001:8000"
```

### Clear and Restart

```bash
# Stop and remove everything
docker-compose down -v

# Rebuild from scratch
docker-compose up -d --build
```

### View Container Logs

```bash
docker-compose -f Docker/docker-compose.yml logs -f [service_name]
```

## 📂 File Structure

All Docker files are in the `Docker/` directory:
- `Docker/Dockerfile` - Container definition
- `Docker/docker-compose.yml` - Development config
- `Docker/docker-compose.prod.yml` - Production config
- `Docker/docker-setup.sh` - Setup script
- `Docker/Makefile` - Command shortcuts

## 📚 More Information

See `README.Docker.md` for detailed documentation.

