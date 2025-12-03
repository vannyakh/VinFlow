#!/bin/bash

###############################################################################
# VinFlow System Requirements Checker
# Run this script to verify server meets requirements before deployment
###############################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "================================================"
echo "VinFlow System Requirements Check"
echo "================================================"
echo ""

passed=0
failed=0
warnings=0

# Function to check command existence
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 is installed"
        ((passed++))
        return 0
    else
        echo -e "${RED}✗${NC} $1 is NOT installed"
        ((failed++))
        return 1
    fi
}

# Function to check version
check_version() {
    local cmd=$1
    local min_version=$2
    local current_version=$3
    
    if [ -z "$current_version" ]; then
        echo -e "${YELLOW}⚠${NC} Cannot determine $cmd version"
        ((warnings++))
        return 1
    fi
    
    echo -e "${BLUE}ℹ${NC} $cmd version: $current_version"
    return 0
}

# Check OS
echo "Operating System:"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo -e "${BLUE}ℹ${NC} OS: $NAME $VERSION"
    if [[ "$ID" == "ubuntu" ]] && [[ "$VERSION_ID" == "22.04" || "$VERSION_ID" == "24.04" ]]; then
        echo -e "${GREEN}✓${NC} OS is compatible"
        ((passed++))
    else
        echo -e "${YELLOW}⚠${NC} Recommended OS: Ubuntu 22.04 or 24.04 LTS"
        ((warnings++))
    fi
else
    echo -e "${YELLOW}⚠${NC} Cannot determine OS"
    ((warnings++))
fi
echo ""

# Check Python
echo "Python:"
check_command python3
if command -v python3 &> /dev/null; then
    py_version=$(python3 --version | awk '{print $2}')
    check_version "Python" "3.10" "$py_version"
    major=$(echo $py_version | cut -d. -f1)
    minor=$(echo $py_version | cut -d. -f2)
    if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
        echo -e "${GREEN}✓${NC} Python version is compatible (>= 3.10)"
        ((passed++))
    else
        echo -e "${RED}✗${NC} Python version too old (need >= 3.10)"
        ((failed++))
    fi
fi
check_command pip3
check_command python3-venv || check_command virtualenv
echo ""

# Check PostgreSQL
echo "PostgreSQL:"
check_command psql
if command -v psql &> /dev/null; then
    pg_version=$(psql --version | awk '{print $3}')
    check_version "PostgreSQL" "14" "$pg_version"
fi
if systemctl is-active --quiet postgresql 2>/dev/null; then
    echo -e "${GREEN}✓${NC} PostgreSQL service is running"
    ((passed++))
else
    echo -e "${RED}✗${NC} PostgreSQL service is not running"
    ((failed++))
fi
echo ""

# Check Redis
echo "Redis:"
check_command redis-server
check_command redis-cli
if command -v redis-cli &> /dev/null; then
    redis_version=$(redis-cli --version | awk '{print $2}')
    check_version "Redis" "6.0" "$redis_version"
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✓${NC} Redis is responding"
        ((passed++))
    else
        echo -e "${RED}✗${NC} Redis is not responding"
        ((failed++))
    fi
fi
if systemctl is-active --quiet redis 2>/dev/null || systemctl is-active --quiet redis-server 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Redis service is running"
    ((passed++))
else
    echo -e "${RED}✗${NC} Redis service is not running"
    ((failed++))
fi
echo ""

# Check Nginx
echo "Nginx:"
check_command nginx
if command -v nginx &> /dev/null; then
    nginx_version=$(nginx -v 2>&1 | awk -F'/' '{print $2}')
    check_version "Nginx" "1.18" "$nginx_version"
fi
if systemctl is-active --quiet nginx 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Nginx service is running"
    ((passed++))
else
    echo -e "${YELLOW}⚠${NC} Nginx service is not running"
    ((warnings++))
fi
echo ""

# Check Git
echo "Version Control:"
check_command git
if command -v git &> /dev/null; then
    git_version=$(git --version | awk '{print $3}')
    check_version "Git" "2.0" "$git_version"
fi
echo ""

# Check System Tools
echo "System Tools:"
check_command curl
check_command wget
check_command nano || check_command vim
check_command systemctl
check_command ufw || echo -e "${YELLOW}⚠${NC} ufw (firewall) not installed"
echo ""

# Check Build Tools
echo "Build Tools:"
check_command gcc
check_command make
echo -e "${BLUE}ℹ${NC} Checking for development packages..."
if dpkg -s build-essential &> /dev/null; then
    echo -e "${GREEN}✓${NC} build-essential is installed"
    ((passed++))
else
    echo -e "${RED}✗${NC} build-essential is NOT installed"
    ((failed++))
fi
if dpkg -s libpq-dev &> /dev/null; then
    echo -e "${GREEN}✓${NC} libpq-dev is installed"
    ((passed++))
else
    echo -e "${RED}✗${NC} libpq-dev is NOT installed"
    ((failed++))
fi
echo ""

# Check System Resources
echo "System Resources:"
total_ram=$(free -m | awk 'NR==2{print $2}')
echo -e "${BLUE}ℹ${NC} Total RAM: ${total_ram}MB"
if [ "$total_ram" -ge 2000 ]; then
    echo -e "${GREEN}✓${NC} RAM is sufficient (>= 2GB)"
    ((passed++))
else
    echo -e "${YELLOW}⚠${NC} RAM is low (< 2GB), 2GB+ recommended"
    ((warnings++))
fi

cpu_cores=$(nproc)
echo -e "${BLUE}ℹ${NC} CPU Cores: ${cpu_cores}"
if [ "$cpu_cores" -ge 2 ]; then
    echo -e "${GREEN}✓${NC} CPU cores sufficient (>= 2)"
    ((passed++))
else
    echo -e "${YELLOW}⚠${NC} Only 1 CPU core, 2+ recommended"
    ((warnings++))
fi

disk_space=$(df -h / | awk 'NR==2{print $4}')
echo -e "${BLUE}ℹ${NC} Available disk space: ${disk_space}"
disk_gb=$(df -BG / | awk 'NR==2{print $4}' | sed 's/G//')
if [ "$disk_gb" -ge 20 ]; then
    echo -e "${GREEN}✓${NC} Disk space sufficient (>= 20GB)"
    ((passed++))
else
    echo -e "${YELLOW}⚠${NC} Low disk space (< 20GB), 40GB+ recommended"
    ((warnings++))
fi
echo ""

# Check Ports
echo "Network Ports:"
check_port() {
    local port=$1
    local service=$2
    if netstat -tuln 2>/dev/null | grep -q ":${port} " || ss -tuln 2>/dev/null | grep -q ":${port} "; then
        echo -e "${BLUE}ℹ${NC} Port ${port} is in use (${service})"
    else
        echo -e "${YELLOW}⚠${NC} Port ${port} is not in use (${service} may not be running)"
    fi
}

check_port 80 "HTTP"
check_port 443 "HTTPS"
check_port 5432 "PostgreSQL"
check_port 6379 "Redis"
echo ""

# Summary
echo "================================================"
echo "Summary"
echo "================================================"
echo -e "${GREEN}Passed:${NC} $passed"
echo -e "${YELLOW}Warnings:${NC} $warnings"
echo -e "${RED}Failed:${NC} $failed"
echo ""

if [ $failed -eq 0 ]; then
    if [ $warnings -eq 0 ]; then
        echo -e "${GREEN}✓ All requirements met! Ready for deployment.${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠ Some warnings found. Review before deployment.${NC}"
        exit 0
    fi
else
    echo -e "${RED}✗ Some requirements not met. Install missing components.${NC}"
    echo ""
    echo "Quick install commands for Ubuntu:"
    echo "  sudo apt update"
    echo "  sudo apt install -y python3 python3-pip python3-venv python3-dev"
    echo "  sudo apt install -y postgresql postgresql-contrib"
    echo "  sudo apt install -y redis-server"
    echo "  sudo apt install -y nginx"
    echo "  sudo apt install -y git curl wget"
    echo "  sudo apt install -y build-essential libpq-dev"
    exit 1
fi

