#!/bin/bash

###############################################################################
# VinFlow Django Application Deployment Script for aaPanel
# This script automates the deployment process on aaPanel
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - Update these values for your aaPanel setup
PROJECT_NAME="vinflow"
# aaPanel typically uses /www/wwwroot/ for web projects
PROJECT_DIR="/www/wwwroot/${PROJECT_NAME}"
VENV_DIR="${PROJECT_DIR}/venv"
GIT_REPO="https://github.com/vannyakh/vinflow.git"  # Update this
BRANCH="main"
AAPANEL_USER="www"  # Default aaPanel user, change if different

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

print_info() {
    echo -e "${BLUE}INFO:${NC} $1"
}

# Check if aaPanel is installed
check_aapanel() {
    if [ ! -d "/www/server/panel" ]; then
        print_warning "aaPanel directory not found at /www/server/panel"
        print_info "This script assumes aaPanel is installed. Continuing anyway..."
    else
        print_message "aaPanel detected"
    fi
}

# Check if project directory exists
check_project_dir() {
    if [ ! -d "${PROJECT_DIR}" ]; then
        print_error "Project directory ${PROJECT_DIR} not found!"
        print_info "Please create the project in aaPanel first:"
        print_info "1. Go to aaPanel > Website > Python Project"
        print_info "2. Add a new Python project"
        print_info "3. Set the project path to ${PROJECT_DIR}"
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
        print_message "Code updated to latest ${BRANCH} branch"
    else
        print_error "Git repository not found. Please clone it first."
        print_info "Run: git clone ${GIT_REPO} ${PROJECT_DIR}"
        exit 1
    fi
}

# Install/Update Python dependencies
install_dependencies() {
    print_message "Installing Python dependencies..."
    
    if [ ! -d "${VENV_DIR}" ]; then
        print_warning "Virtual environment not found at ${VENV_DIR}"
        print_info "Creating virtual environment..."
        python3 -m venv ${VENV_DIR}
    fi
    
    source ${VENV_DIR}/bin/activate
    pip install --upgrade pip
    pip install -r ${PROJECT_DIR}/requirements.txt
    print_message "Dependencies installed successfully"
}

# Collect static files
collect_static() {
    print_message "Collecting static files..."
    source ${VENV_DIR}/bin/activate
    cd ${PROJECT_DIR}
    python manage.py collectstatic --noinput
    print_message "Static files collected"
}

# Run database migrations
run_migrations() {
    print_message "Running database migrations..."
    source ${VENV_DIR}/bin/activate
    cd ${PROJECT_DIR}
    python manage.py migrate --noinput
    print_message "Database migrations completed"
}

# Compile translation messages
compile_messages() {
    print_message "Compiling translation messages..."
    source ${VENV_DIR}/bin/activate
    cd ${PROJECT_DIR}
    
    if [ -d "locale" ]; then
        python manage.py compilemessages
        print_message "Translation messages compiled"
    else
        print_warning "No locale directory found, skipping message compilation"
    fi
}

# Set proper permissions for aaPanel
set_permissions() {
    print_message "Setting proper file permissions..."
    
    # Set ownership to aaPanel user
    chown -R ${AAPANEL_USER}:${AAPANEL_USER} ${PROJECT_DIR}
    
    # Set directory permissions
    find ${PROJECT_DIR} -type d -exec chmod 755 {} \;
    
    # Set file permissions
    find ${PROJECT_DIR} -type f -exec chmod 644 {} \;
    
    # Make scripts executable
    if [ -f "${PROJECT_DIR}/manage.py" ]; then
        chmod +x ${PROJECT_DIR}/manage.py
    fi
    
    # Make sure media directory is writable
    if [ -d "${PROJECT_DIR}/media" ]; then
        chmod -R 775 ${PROJECT_DIR}/media
    fi
    
    # Make sure log directories are writable if they exist
    if [ -d "${PROJECT_DIR}/logs" ]; then
        chmod -R 775 ${PROJECT_DIR}/logs
    fi
    
    print_message "Permissions set successfully"
}

# Restart Python application in aaPanel
restart_application() {
    print_message "Restarting Python application..."
    
    # Try to restart using aaPanel CLI if available
    if command -v bt &> /dev/null; then
        print_info "Using aaPanel CLI to restart application..."
        bt restart
    else
        print_warning "aaPanel CLI not found"
        print_info "Please restart the application manually in aaPanel:"
        print_info "1. Go to aaPanel > Website > Python Project"
        print_info "2. Find '${PROJECT_NAME}' and click 'Restart'"
    fi
    
    # Kill any existing Gunicorn processes for this project
    print_info "Stopping existing Gunicorn processes..."
    pkill -f "gunicorn.*${PROJECT_NAME}" || true
    
    # Restart Celery workers if they exist
    if [ -f "${PROJECT_DIR}/celery.pid" ]; then
        print_info "Restarting Celery workers..."
        pkill -f "celery.*${PROJECT_NAME}" || true
        rm -f ${PROJECT_DIR}/celery.pid
    fi
    
    print_message "Application restart initiated"
}

# Check application status
check_status() {
    print_message "Checking application status..."
    
    # Check if Gunicorn is running
    if pgrep -f "gunicorn.*${PROJECT_NAME}" > /dev/null; then
        echo -e "${GREEN}✓${NC} Gunicorn is running"
    else
        echo -e "${YELLOW}⚠${NC} Gunicorn process not found"
    fi
    
    # Check if Celery is running
    if pgrep -f "celery.*${PROJECT_NAME}" > /dev/null; then
        echo -e "${GREEN}✓${NC} Celery is running"
    else
        echo -e "${YELLOW}⚠${NC} Celery process not found (may be optional)"
    fi
    
    # Check if Redis is running (if used)
    if pgrep -f "redis-server" > /dev/null; then
        echo -e "${GREEN}✓${NC} Redis is running"
    else
        echo -e "${YELLOW}⚠${NC} Redis process not found (may be optional)"
    fi
}

# Safely read a value from .env file
get_env_value() {
    local key=$1
    local env_file="${PROJECT_DIR}/.env"
    
    if [ -f "$env_file" ]; then
        # Use grep to find the line, then extract the value after =
        grep "^${key}=" "$env_file" | cut -d '=' -f 2- | tr -d '\r\n' | tr -d '"' | tr -d "'"
    fi
}

# Create backup
create_backup() {
    print_message "Creating database backup..."
    BACKUP_DIR="${PROJECT_DIR}/backups"
    mkdir -p ${BACKUP_DIR}
    
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"
    
    # Load environment variables safely using our helper function
    if [ -f "${PROJECT_DIR}/.env" ]; then
        # Read database configuration from .env
        DB_ENGINE=$(get_env_value "DB_ENGINE")
        DB_NAME=$(get_env_value "DB_NAME")
        DB_USER=$(get_env_value "DB_USER")
        DB_PASSWORD=$(get_env_value "DB_PASSWORD")
        DB_HOST=$(get_env_value "DB_HOST")
        
        # Set default host if not specified
        DB_HOST=${DB_HOST:-localhost}
        
        # Check database type and create appropriate backup
        if [ ! -z "${DB_NAME}" ]; then
            if [[ "${DB_ENGINE}" == *"postgresql"* ]]; then
                # PostgreSQL backup
                print_info "Creating PostgreSQL backup..."
                if command -v pg_dump &> /dev/null; then
                    PGPASSWORD="${DB_PASSWORD}" pg_dump -U "${DB_USER}" -h "${DB_HOST}" "${DB_NAME}" > "${BACKUP_FILE}" 2>/dev/null
                    if [ $? -eq 0 ]; then
                        gzip "${BACKUP_FILE}"
                        print_message "Backup created: ${BACKUP_FILE}.gz"
                    else
                        print_warning "PostgreSQL backup failed"
                        rm -f "${BACKUP_FILE}"
                    fi
                else
                    print_warning "pg_dump not found, skipping PostgreSQL backup"
                fi
            elif [[ "${DB_ENGINE}" == *"mysql"* ]]; then
                # MySQL backup
                print_info "Creating MySQL backup..."
                if command -v mysqldump &> /dev/null; then
                    mysqldump -u "${DB_USER}" -p"${DB_PASSWORD}" -h "${DB_HOST}" "${DB_NAME}" > "${BACKUP_FILE}" 2>/dev/null
                    if [ $? -eq 0 ]; then
                        gzip "${BACKUP_FILE}"
                        print_message "Backup created: ${BACKUP_FILE}.gz"
                    else
                        print_warning "MySQL backup failed"
                        rm -f "${BACKUP_FILE}"
                    fi
                else
                    print_warning "mysqldump not found, skipping MySQL backup"
                fi
            else
                # SQLite backup
                if [ -f "${PROJECT_DIR}/db.sqlite3" ]; then
                    print_info "Creating SQLite backup..."
                    cp "${PROJECT_DIR}/db.sqlite3" "${BACKUP_DIR}/db_${TIMESTAMP}.sqlite3"
                    gzip "${BACKUP_DIR}/db_${TIMESTAMP}.sqlite3"
                    print_message "Backup created: ${BACKUP_DIR}/db_${TIMESTAMP}.sqlite3.gz"
                else
                    print_info "No SQLite database file found"
                fi
            fi
        else
            print_info "No database name configured, skipping backup"
        fi
    else
        print_warning "No .env file found, skipping database backup"
    fi
    
    # Keep only last 10 backups
    print_info "Cleaning old backups (keeping last 10)..."
    ls -t ${BACKUP_DIR}/backup_*.sql.gz 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
    ls -t ${BACKUP_DIR}/db_*.sqlite3.gz 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
}

# Display post-deployment instructions
post_deployment_info() {
    print_message "Post-deployment checklist:"
    echo ""
    echo -e "${BLUE}1.${NC} Verify the application in aaPanel:"
    echo "   - Go to: Website > Python Project"
    echo "   - Check '${PROJECT_NAME}' status"
    echo ""
    echo -e "${BLUE}2.${NC} Test your application:"
    echo "   - Visit your domain in a browser"
    echo "   - Check all main features work correctly"
    echo ""
    echo -e "${BLUE}3.${NC} Monitor logs:"
    echo "   - Check aaPanel logs: /www/wwwlogs/"
    echo "   - Check application logs: ${PROJECT_DIR}/logs/"
    echo ""
    echo -e "${BLUE}4.${NC} If application doesn't start:"
    echo "   - Check aaPanel Python Project settings"
    echo "   - Verify .env file exists and is correct"
    echo "   - Check file permissions"
    echo "   - Review error logs"
}

# Main deployment function
main() {
    echo ""
    print_message "╔════════════════════════════════════════════╗"
    print_message "║  VinFlow Deployment Script for aaPanel    ║"
    print_message "╚════════════════════════════════════════════╝"
    echo ""
    
    check_aapanel
    check_project_dir
    create_backup
    pull_code
    install_dependencies
    run_migrations
    compile_messages
    collect_static
    set_permissions
    restart_application
    
    echo ""
    check_status
    echo ""
    
    print_message "═══════════════════════════════════════════"
    print_message "Deployment completed successfully! 🎉"
    print_message "═══════════════════════════════════════════"
    echo ""
    
    post_deployment_info
}

# Run main function
main

