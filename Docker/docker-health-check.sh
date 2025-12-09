#!/bin/bash
# Docker Health Check Script for VinFlow

# Change to project root directory
cd "$(dirname "$0")/.."

COMPOSE_FILE="Docker/docker-compose.yml"

echo "======================================"
echo "VinFlow Docker Health Check"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_service() {
    local service=$1
    if docker-compose -f $COMPOSE_FILE ps | grep -q "$service.*Up"; then
        echo -e "${GREEN}✓${NC} $service is running"
        return 0
    else
        echo -e "${RED}✗${NC} $service is not running"
        return 1
    fi
}

check_port() {
    local port=$1
    local service=$2
    if nc -z localhost $port 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Port $port ($service) is accessible"
        return 0
    else
        echo -e "${RED}✗${NC} Port $port ($service) is not accessible"
        return 1
    fi
}

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}✗${NC} Docker is not running"
    exit 1
fi
echo -e "${GREEN}✓${NC} Docker is running"
echo ""

# Check services
echo "Checking Services:"
echo "-------------------"
check_service "vinflow_web"
check_service "vinflow_db"
check_service "vinflow_redis"
check_service "vinflow_celery_worker"
check_service "vinflow_celery_beat"
echo ""

# Check ports
echo "Checking Ports:"
echo "----------------"
check_port 8000 "Web Application"
check_port 5432 "PostgreSQL"
check_port 6379 "Redis"
echo ""

# Check Django
echo "Checking Django:"
echo "-----------------"
if docker-compose -f $COMPOSE_FILE exec -T web python manage.py check --deploy 2>/dev/null | grep -q "System check identified no issues"; then
    echo -e "${GREEN}✓${NC} Django system check passed"
else
    echo -e "${YELLOW}⚠${NC} Django system check has warnings (check with: docker-compose -f $COMPOSE_FILE exec web python manage.py check --deploy)"
fi
echo ""

# Check database connection
echo "Checking Database:"
echo "-------------------"
if docker-compose -f $COMPOSE_FILE exec -T web python -c "import django; django.setup(); from django.db import connection; connection.ensure_connection(); print('OK')" 2>/dev/null | grep -q "OK"; then
    echo -e "${GREEN}✓${NC} Database connection successful"
else
    echo -e "${RED}✗${NC} Database connection failed"
fi
echo ""

# Check Redis connection
echo "Checking Redis:"
echo "----------------"
if docker-compose -f $COMPOSE_FILE exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
    echo -e "${GREEN}✓${NC} Redis connection successful"
else
    echo -e "${RED}✗${NC} Redis connection failed"
fi
echo ""

# Check migrations
echo "Checking Migrations:"
echo "---------------------"
PENDING_MIGRATIONS=$(docker-compose -f $COMPOSE_FILE exec -T web python manage.py showmigrations --plan 2>/dev/null | grep "\[ \]" | wc -l)
if [ $PENDING_MIGRATIONS -eq 0 ]; then
    echo -e "${GREEN}✓${NC} All migrations applied"
else
    echo -e "${YELLOW}⚠${NC} $PENDING_MIGRATIONS pending migration(s)"
    echo "  Run: docker-compose -f $COMPOSE_FILE exec web python manage.py migrate"
fi
echo ""

# Resource usage
echo "Resource Usage:"
echo "----------------"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep vinflow
echo ""

echo "======================================"
echo "Health Check Complete"
echo "======================================"
echo ""
echo "Access your application at: http://localhost:8000"
echo ""

