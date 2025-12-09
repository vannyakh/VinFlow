# VinFlow Docker Configuration

This directory contains all Docker-related files for the VinFlow project.

## 📁 Files

- **`Dockerfile`** - Container definition for the Django application
- **`docker-compose.yml`** - Development environment configuration
- **`docker-compose.prod.yml`** - Production environment configuration
- **`docker-setup.sh`** - Automated setup script
- **`docker-health-check.sh`** - Health check and monitoring script
- **`docker-entrypoint.sh`** - Container initialization script
- **`Makefile`** - Quick command shortcuts
- **`.dockerignore`** - Files to exclude from Docker builds

## 🚀 Quick Start

### From Project Root

```bash
# Automated setup
./Docker/docker-setup.sh

# Or use make commands
make -f Makefile.docker up-build
make -f Makefile.docker createsuperuser

# Or use docker-compose directly
docker-compose -f Docker/docker-compose.yml up -d --build
```

### From Docker Directory

```bash
cd Docker

# Using make
make up-build
make createsuperuser
make logs

# Or using docker-compose
docker-compose up -d --build
docker-compose logs -f
```

## 🛠️ Common Commands

### Using Make (Recommended)

From the Docker directory:

```bash
make help              # Show all available commands
make up-build          # Build and start services
make logs              # View logs
make shell             # Django shell
make migrate           # Run migrations
make createsuperuser   # Create superuser
make down              # Stop services
make health            # Run health check
```

### Using Docker Compose

From the Docker directory:

```bash
docker-compose up -d                              # Start services
docker-compose down                               # Stop services
docker-compose logs -f                            # View logs
docker-compose exec web python manage.py shell   # Django shell
docker-compose ps                                 # Check status
```

## 📍 Services

The Docker setup includes 5 services:

1. **web** - Django application (port 8000)
2. **db** - PostgreSQL 16 database (port 5432)
3. **redis** - Redis cache and broker (port 6379)
4. **celery_worker** - Background task processor
5. **celery_beat** - Scheduled task scheduler

## ⚙️ Configuration

Environment variables are configured in the `.env` file in the project root.

Template: `../env.docker.example`

Key variables:
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode
- `DB_PASSWORD` - Database password
- Payment gateway credentials
- OAuth settings

## 📖 Full Documentation

See the documentation files in the `docs/` directory:

- `../docs/README.Docker.md` - Comprehensive guide
- `../docs/DOCKER_QUICK_START.md` - Quick reference
- `../docs/DOCKER_SETUP_COMPLETE.md` - Setup summary

## 🔧 Nginx Configuration

Nginx configuration files are in the `../nginx/` directory:

- `../nginx/nginx.conf` - Main Nginx configuration
- `../nginx/conf.d/default.conf` - Site configuration

## 📊 Health Check

Run the health check script to verify all services:

```bash
./docker-health-check.sh
```

## 🎯 Tips

1. **Always run commands from the project root** or adjust paths accordingly
2. **Use `make` commands** for convenience
3. **Check logs** if something doesn't work: `make logs`
4. **Run health check** after starting services: `make health`
5. **Keep `.env` file** in project root, not in Docker directory

## 🔄 Workflow

1. Start services: `make up-build`
2. Create superuser: `make createsuperuser`
3. Make code changes (auto-reload enabled)
4. Run migrations: `make migrate`
5. View logs: `make logs`
6. Stop services: `make down`

## 🚨 Troubleshooting

### Services not starting

```bash
# Check logs
make logs

# Rebuild
make clean
make up-build
```

### Port conflicts

Edit `docker-compose.yml` and change port mappings.

### Database issues

```bash
# Check database
make db-shell

# Reset (WARNING: Deletes data)
make clean
make up-build
```

## 📦 Production

For production deployment:

```bash
# From Docker directory
make prod-build
make prod-up
make prod-logs
```

Or from project root:

```bash
docker-compose -f Docker/docker-compose.prod.yml up -d --build
```

---

For more information, see the main documentation in `docs/README.Docker.md`

