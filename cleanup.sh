#!/bin/bash

# Excelpoint Development Environment Cleanup Script
# ===============================================
#
# This script performs a comprehensive cleanup of the development environment,
# removing temporary files, cache directories, and virtual environments to
# ensure a clean state for development or deployment.
#
# What it cleans up:
# - Virtual environment directories (venv, venv-py312, etc.)
# - SQLite database files
# - Python cache files (__pycache__, *.pyc)
# - OS-specific files (.DS_Store, Thumbs.db)
# - Temporary cache directories
#
# What it sets up:
# - Creates a comprehensive .gitignore file if missing
# - Initializes git repository if not present
# - Provides instructions for GitHub setup
#
# Usage: ./cleanup.sh
# Requirements: bash shell, git (optional)

# Remove virtual environment directories
echo "Removing virtual environment directories..."
rm -rf venv/
rm -rf venv_py312/
rm -rf venv-py312/

# Remove database file
echo "Removing database file..."
rm -f db.sqlite3

# Remove cache directory
echo "Removing cache directory..."
rm -rf cache/

# Remove all __pycache__ directories
echo "Removing Python cache files..."
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -type f -delete

# Remove .DS_Store files
echo "Removing .DS_Store files..."
find . -name ".DS_Store" -type f -delete

# Create .gitignore if not exists
if [ ! -f .gitignore ]; then
    echo "Creating .gitignore file..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
venv-py312/
venv_py312/
ENV/

# Django
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal
media

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Custom
cache/
EOF
fi

echo "Cleanup complete!"

# Initialize git repository if not already done
if [ ! -d .git ]; then
    echo "Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit"
else
    echo "Git repository already exists."
fi

echo "You can now push the repository to GitHub with the following commands:"
echo "git remote add origin <your-github-repo-url>"
echo "git push -u origin main" 