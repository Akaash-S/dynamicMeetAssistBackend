#!/bin/bash
# Fix permissions for Docker socket
sudo chmod 666 /var/run/docker.sock

# Create .env from example if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env from env.example..."
    cp env.example .env
fi

echo "Docker permissions fixed available."
echo "Please edit .env with your actual keys before running docker-compose up."
