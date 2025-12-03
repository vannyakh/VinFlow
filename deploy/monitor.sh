#!/bin/bash

###############################################################################
# VinFlow System Monitoring Script
# Checks health of all services and sends alerts if needed
###############################################################################

PROJECT_NAME="vinflow"
EMAIL_ALERT="admin@your-domain.com"  # Change this to your email
SEND_EMAIL=false  # Set to true if you want email alerts

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if service is running
check_service() {
    local service=$1
    if systemctl is-active --quiet $service; then
        echo -e "${GREEN}✓${NC} $service is running"
        return 0
    else
        echo -e "${RED}✗${NC} $service is NOT running"
        return 1
    fi
}

# Check disk space
check_disk_space() {
    local threshold=80
    local usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ $usage -lt $threshold ]; then
        echo -e "${GREEN}✓${NC} Disk usage: ${usage}%"
        return 0
    else
        echo -e "${RED}✗${NC} Disk usage: ${usage}% (threshold: ${threshold}%)"
        return 1
    fi
}

# Check memory
check_memory() {
    local threshold=90
    local usage=$(free | awk 'NR==2 {printf "%.0f", $3*100/$2}')
    
    if [ $usage -lt $threshold ]; then
        echo -e "${GREEN}✓${NC} Memory usage: ${usage}%"
        return 0
    else
        echo -e "${RED}✗${NC} Memory usage: ${usage}% (threshold: ${threshold}%)"
        return 1
    fi
}

# Check PostgreSQL
check_postgresql() {
    if systemctl is-active --quiet postgresql; then
        if psql -U postgres -c '\l' > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} PostgreSQL is accessible"
            return 0
        else
            echo -e "${RED}✗${NC} PostgreSQL is not accessible"
            return 1
        fi
    else
        echo -e "${RED}✗${NC} PostgreSQL is not running"
        return 1
    fi
}

# Check Redis
check_redis() {
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Redis is responding"
        return 0
    else
        echo -e "${RED}✗${NC} Redis is not responding"
        return 1
    fi
}

# Check website response
check_website() {
    local url="http://localhost:8000/health/"
    local response=$(curl -s -o /dev/null -w "%{http_code}" $url)
    
    if [ $response -eq 200 ]; then
        echo -e "${GREEN}✓${NC} Website is responding (HTTP $response)"
        return 0
    else
        echo -e "${RED}✗${NC} Website is not responding properly (HTTP $response)"
        return 1
    fi
}

# Main monitoring
echo "================================================"
echo "VinFlow System Health Check - $(date)"
echo "================================================"
echo ""

failed=0

echo "Services Status:"
check_service "${PROJECT_NAME}-gunicorn" || failed=$((failed+1))
check_service "${PROJECT_NAME}-celery" || failed=$((failed+1))
check_service "${PROJECT_NAME}-celerybeat" || failed=$((failed+1))
check_service "nginx" || failed=$((failed+1))
check_service "redis" || failed=$((failed+1))

echo ""
echo "Database Status:"
check_postgresql || failed=$((failed+1))
check_redis || failed=$((failed+1))

echo ""
echo "System Resources:"
check_disk_space || failed=$((failed+1))
check_memory || failed=$((failed+1))

echo ""
echo "Application Health:"
check_website || failed=$((failed+1))

echo ""
echo "================================================"

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}$failed check(s) failed!${NC}"
    
    # Send email alert if enabled
    if [ "$SEND_EMAIL" = true ]; then
        echo "VinFlow monitoring detected $failed failed checks on $(hostname) at $(date)" | \
        mail -s "ALERT: VinFlow Health Check Failed" $EMAIL_ALERT
    fi
    
    exit 1
fi

