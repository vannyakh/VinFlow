#!/bin/bash

###############################################################################
# Add gunicorn to requirements.txt if not present
###############################################################################

REQUIREMENTS_FILE="requirements.txt"

# Check if gunicorn is already in requirements
if ! grep -q "gunicorn" $REQUIREMENTS_FILE; then
    echo "Adding gunicorn to requirements.txt..."
    echo "gunicorn>=21.2.0" >> $REQUIREMENTS_FILE
    echo "✓ Added gunicorn to requirements.txt"
else
    echo "✓ gunicorn already in requirements.txt"
fi

# Check if django-compressor is in requirements
if ! grep -q "django-compressor" $REQUIREMENTS_FILE; then
    echo "Adding django-compressor to requirements.txt..."
    echo "django-compressor>=4.4" >> $REQUIREMENTS_FILE
    echo "✓ Added django-compressor to requirements.txt"
else
    echo "✓ django-compressor already in requirements.txt"
fi

echo "Requirements check complete!"

