#!/bin/bash

echo "Setting up Career Nexus Docker environment..."

# Create base requirements file (without spaCy)
echo "Creating base requirements file..."
grep -v "spacy" requirements.txt > requirements-base.txt

echo "Docker setup prepared successfully!"
echo ""
echo "Available Docker configurations:"
echo "--------------------------------"
echo "1. Base version (without spaCy):"
echo "   docker-compose up app"
echo ""
echo "2. Full version (with spaCy):"
echo "   docker-compose up app-spacy"
echo ""
echo "Note: The base version runs on port 8000, while the spaCy version runs on port 8001"
echo "You can access them at:"
echo "  - Base version: http://localhost:8000"
echo "  - Full version: http://localhost:8001" 