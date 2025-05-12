#!/bin/bash
# Simple script to build the Docker image for oai-proxy

# Exit on error
set -e

echo "Building Docker image for oai-proxy..."

# Build the Docker image with tag oai-proxy
docker build -t oai-proxy .

echo "Docker image built successfully!"
echo "You can run the container with: docker run -p 9000:9000 oai-proxy"
