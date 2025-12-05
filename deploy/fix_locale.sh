#!/bin/bash

###############################################################################
# Fix Locale Compilation Issues
###############################################################################

set -e

PROJECT_DIR="/www/wwwroot/vinflow"
VENV_DIR="${PROJECT_DIR}/venv"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Fixing locale compilation issues...${NC}"

cd ${PROJECT_DIR}
source ${VENV_DIR}/bin/activate

# Remove any existing compiled files
echo "Removing old compiled message files..."
find ${PROJECT_DIR}/locale -name "*.mo" -delete

# Fix permissions on locale directory
echo "Setting proper permissions..."
chown -R www:www ${PROJECT_DIR}/locale
chmod -R 755 ${PROJECT_DIR}/locale

# Compile only project locale files (not Django's system files)
echo "Compiling messages for project locale files only..."
cd ${PROJECT_DIR}

# Compile for each locale separately
for lang_dir in locale/*/; do
    if [ -d "$lang_dir" ]; then
        lang=$(basename $lang_dir)
        echo "Compiling messages for language: ${lang}"
        python manage.py compilemessages -l ${lang} --ignore=venv/* 2>&1 || {
            echo -e "${YELLOW}Warning: Could not compile messages for ${lang}${NC}"
        }
    fi
done

echo -e "${GREEN}Locale fix completed!${NC}"

