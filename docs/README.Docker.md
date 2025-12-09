# Docker Setup for VinFlow

This guide will help you set up and run VinFlow using Docker.

## Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)

## File Structure

All Docker files are located in the `Docker/` directory:

```
VinFlow/
├── Docker/
│   ├── Dockerfile                   # Container definition
│   ├── docker-compose.yml           # Development config
│   ├── docker-compose.prod.yml      # Production config
│   ├── docker-setup.sh              # Automated setup
│   ├── docker-health-check.sh       # Health monitoring
│   └── Makefile                     # Command shortcuts
├── nginx/                           # Nginx configuration
├── env.docker.example               # Environment template
└── Makefile.docker                  # Root wrapper
```

## Quick Start

### 1. Environment Setup

Copy the Docker environment template:

```bash
cp env.docker.example .env
```

Edit `.env` and update the values, especially:
- `SECRET_KEY` - Generate a new secret key
- `DB_PASSWORD` - Set a secure database password
- Payment gateway credentials (if using)

### 2. Build and Start Services

#### Option A: Automated Setup (Recommended)

```bash
./Docker/docker-setup.sh
```

#### Option B: Using Make

```bash
make -f Makefile.docker up-build
```

#### Option C: Using Docker Compose

```bash
docker-compose -f Docker/docker-compose.yml up -d --build
```

### 3. Create Superuser

After the services are running, create a Django superuser:

```bash
# Using make
make -f Makefile.docker createsuperuser

# Or using docker-compose
docker-compose -f Docker/docker-compose.yml exec web python manage.py createsuperuser
```

### 4. Access the Application

- **Web Application**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin

## Docker Services

The setup includes the following services:

1. **web** - Django application (port 8000)
2. **db** - PostgreSQL database (port 5432)
3. **redis** - Redis cache and Celery broker (port 6379)
4. **celery_worker** - Celery worker for background tasks
5. **celery_beat** - Celery beat for scheduled tasks

## Common Commands

### Using Make (Recommended)

```bash
# From project root
make -f Makefile.docker help          # Show all commands
make -f Makefile.docker up-build      # Start services
make -f Makefile.docker logs          # View logs
make -f Makefile.docker shell         # Django shell
make -f Makefile.docker migrate       # Run migrations
make -f Makefile.docker down          # Stop services

# Or from Docker directory
cd Docker
make help
make up-build
make logs
```

### View Logs

```bash
# All services
docker-compose -f Docker/docker-compose.yml logs -f

# Specific service
docker-compose -f Docker/docker-compose.yml logs -f web
docker-compose -f Docker/docker-compose.yml logs -f celery_worker
```

### Execute Django Commands

```bash
# Run migrations
docker-compose -f Docker/docker-compose.yml exec web python manage.py migrate

# Create superuser
docker-compose -f Docker/docker-compose.yml exec web python manage.py createsuperuser

# Collect static files
docker-compose -f Docker/docker-compose.yml exec web python manage.py collectstatic

# Make migrations
docker-compose -f Docker/docker-compose.yml exec web python manage.py makemigrations

# Django shell
docker-compose -f Docker/docker-compose.yml exec web python manage.py shell
```

### Database Operations

```bash
# Access PostgreSQL shell
docker-compose -f Docker/docker-compose.yml exec db psql -U postgres -d vinflow_dev

# Backup database
docker-compose -f Docker/docker-compose.yml exec db pg_dump -U postgres vinflow_dev > backup.sql

# Restore database
docker-compose -f Docker/docker-compose.yml exec -T db psql -U postgres vinflow_dev < backup.sql
```

### Redis Operations

```bash
# Access Redis CLI
docker-compose -f Docker/docker-compose.yml exec redis redis-cli

# Flush Redis cache
docker-compose -f Docker/docker-compose.yml exec redis redis-cli FLUSHALL
```

### Stop and Remove Containers

```bash
# Stop services
docker-compose -f Docker/docker-compose.yml stop

# Stop and remove containers
docker-compose -f Docker/docker-compose.yml down

# Remove containers and volumes (WARNING: This deletes data)
docker-compose -f Docker/docker-compose.yml down -v
```

### Rebuild Services

```bash
# Rebuild a specific service
docker-compose -f Docker/docker-compose.yml build web

# Rebuild all services
docker-compose -f Docker/docker-compose.yml build

# Force rebuild without cache
docker-compose -f Docker/docker-compose.yml build --no-cache
```

## Production Deployment

For production, use the production compose file:

```bash
# Build and start
docker-compose -f Docker/docker-compose.prod.yml up -d --build

# View logs
docker-compose -f Docker/docker-compose.prod.yml logs -f

# Or using make
make -f Makefile.docker prod-build
make -f Makefile.docker prod-up
make -f Makefile.docker prod-logs
```

### Production Checklist

1. Update `.env` with production values:
   - Set `DEBUG=False`
   - Generate a strong `SECRET_KEY`
   - Set secure `DB_PASSWORD`
   - Configure `ALLOWED_HOSTS`
   - Add payment gateway credentials

2. Configure Nginx:
   - Create `nginx/conf.d/default.conf`
   - Add SSL certificates in `nginx/ssl/`

3. Set up SSL/TLS certificates (Let's Encrypt recommended)

4. Configure backup strategy for PostgreSQL data

5. Set up monitoring and logging

## Troubleshooting

### Port Already in Use

If port 8000 or 5432 is already in use, update the port mapping in `Docker/docker-compose.yml`:

```yaml
ports:
  - "8001:8000"  # Change host port
```

### Database Connection Issues

Ensure the database service is healthy:

```bash
docker-compose -f Docker/docker-compose.yml ps
docker-compose -f Docker/docker-compose.yml logs db
```

### Permission Issues

If you encounter permission issues with volumes:

```bash
docker-compose -f Docker/docker-compose.yml exec web chown -R 1000:1000 /app/media /app/staticfiles
```

### Clear Everything and Start Fresh

```bash
docker-compose -f Docker/docker-compose.yml down -v
docker system prune -a
docker-compose -f Docker/docker-compose.yml up --build
```

### Health Check

Run the health check script to diagnose issues:

```bash
./Docker/docker-health-check.sh
```

## Development Workflow

1. **Start services**: `make -f Makefile.docker up-build`
2. **Make code changes**: Changes are automatically reflected (Django auto-reload)
3. **Run migrations**: `make -f Makefile.docker migrate`
4. **View logs**: `make -f Makefile.docker logs`
5. **Stop services**: `make -f Makefile.docker down`

## Tips

- Use `docker-compose exec` to run commands inside containers
- Mount your code as a volume for development (already configured)
- Use `.dockerignore` to exclude unnecessary files
- Keep sensitive data in `.env` file (never commit it!)
- Use `docker-compose logs` to debug issues
- Regularly backup your PostgreSQL data

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)

