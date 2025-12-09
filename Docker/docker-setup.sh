#!/bin/bash
# Docker Setup Script for VinFlow

set -e

# Change to project root directory
cd "$(dirname "$0")/.."

echo "======================================"
echo "VinFlow Docker Setup"
echo "======================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp env.docker.example .env
    echo "✓ .env file created"
    echo ""
    echo "IMPORTANT: Please edit .env file and update the following:"
    echo "  - SECRET_KEY: Generate a new secret key"
    echo "  - DB_PASSWORD: Set a secure database password"
    echo "  - Payment gateway credentials (if needed)"
    echo ""
    read -p "Press Enter to continue after updating .env file..."
else
    echo "✓ .env file already exists"
fi

echo ""
echo "Building Docker images..."
docker-compose -f Docker/docker-compose.yml build

echo ""
echo "Starting services..."
docker-compose -f Docker/docker-compose.yml up -d

echo ""
echo "Waiting for services to be ready..."
sleep 10

echo ""
echo "Running migrations..."
docker-compose -f Docker/docker-compose.yml exec -T web python manage.py migrate

echo ""
echo "Collecting static files..."
docker-compose -f Docker/docker-compose.yml exec -T web python manage.py collectstatic --noinput

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Services running:"
docker-compose -f Docker/docker-compose.yml ps

echo ""
echo "Access the application at: http://localhost:8000"
echo ""
echo "To create a superuser, run:"
echo "  docker-compose -f Docker/docker-compose.yml exec web python manage.py createsuperuser"
echo ""
echo "To view logs:"
echo "  docker-compose -f Docker/docker-compose.yml logs -f"
echo ""
echo "To stop services:"
echo "  docker-compose -f Docker/docker-compose.yml down"
echo ""

