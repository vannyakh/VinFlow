#!/bin/bash

###############################################################################
# VinFlow Django Application Deployment Script for Vultr
# This script automates the deployment process
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="vinflow"
PROJECT_DIR="/var/www/${PROJECT_NAME}"
VENV_DIR="${PROJECT_DIR}/venv"
GIT_REPO="https://github.com/yourusername/vinflow.git"  # Update this
BRANCH="main"

# Print colored message
print_message() {
    echo -e "${GREEN}==>${NC} $1"
}

print_error() {
    echo -e "${RED}ERROR:${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

# Check if running as root or with sudo
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root or with sudo"
        exit 1
    fi
}

# Pull latest code from git
pull_code() {
    print_message "Pulling latest code from git..."
    cd ${PROJECT_DIR}
    
    if [ -d ".git" ]; then
        git fetch origin ${BRANCH}
        git reset --hard origin/${BRANCH}
    else
        print_error "Git repository not found. Please clone it first."
        exit 1
    fi
}

# Install/Update Python dependencies
install_dependencies() {
    print_message "Installing Python dependencies..."
    source ${VENV_DIR}/bin/activate
    pip install --upgrade pip
    pip install -r ${PROJECT_DIR}/requirements.txt
}

# Collect static files
collect_static() {
    print_message "Collecting static files..."
    source ${VENV_DIR}/bin/activate
    cd ${PROJECT_DIR}
    python manage.py collectstatic --noinput
}

# Run database migrations
run_migrations() {
    print_message "Running database migrations..."
    source ${VENV_DIR}/bin/activate
    cd ${PROJECT_DIR}
    python manage.py migrate --noinput
}

# Compile translation messages
compile_messages() {
    print_message "Compiling translation messages..."
    source ${VENV_DIR}/bin/activate
    cd ${PROJECT_DIR}
    python manage.py compilemessages
}

# Set proper permissions
set_permissions() {
    print_message "Setting proper file permissions..."
    chown -R www-data:www-data ${PROJECT_DIR}
    chmod -R 755 ${PROJECT_DIR}
    
    # Make sure media and log directories are writable
    chmod -R 775 ${PROJECT_DIR}/media
    chmod -R 775 /var/log/${PROJECT_NAME}
}

# Restart services
restart_services() {
    print_message "Restarting services..."
    systemctl restart ${PROJECT_NAME}-gunicorn
    systemctl restart ${PROJECT_NAME}-celery
    systemctl restart ${PROJECT_NAME}-celerybeat
    systemctl restart nginx
}

# Check service status
check_services() {
    print_message "Checking service status..."
    
    services=("${PROJECT_NAME}-gunicorn" "${PROJECT_NAME}-celery" "${PROJECT_NAME}-celerybeat" "nginx")
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet ${service}; then
            echo -e "${GREEN}✓${NC} ${service} is running"
        else
            echo -e "${RED}✗${NC} ${service} is not running"
        fi
    done
}

# Create backup
create_backup() {
    print_message "Creating database backup..."
    BACKUP_DIR="/var/backups/${PROJECT_NAME}"
    mkdir -p ${BACKUP_DIR}
    
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"
    
    # Source environment variables
    if [ -f "${PROJECT_DIR}/.env" ]; then
        export $(cat ${PROJECT_DIR}/.env | grep -v '^#' | xargs)
        pg_dump -U ${DB_USER} -h ${DB_HOST} ${DB_NAME} > ${BACKUP_FILE}
        gzip ${BACKUP_FILE}
        print_message "Backup created: ${BACKUP_FILE}.gz"
    else
        print_warning "No .env file found, skipping database backup"
    fi
}

# Main deployment function
main() {
    print_message "Starting deployment of VinFlow application..."
    
    check_root
    create_backup
    pull_code
    install_dependencies
    run_migrations
    compile_messages
    collect_static
    set_permissions
    restart_services
    check_services
    
    print_message "Deployment completed successfully!"
    print_message "Access your application at: https://your-domain.com"
}

# Run main function
main

