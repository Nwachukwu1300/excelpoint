#!/usr/bin/env python
"""
Career Nexus Database Reset and Setup Script
--------------------------------------------

This script provides a complete database reset and initialization for the
Excelpoint learning platform. It's designed for development environments
and fresh installations where you need a clean slate with sample data.

The script performs the following operations:
1. Flush the database (remove all existing data)
2. Create a default superuser account
3. Load initial career data and sample content
4. Set up basic application structure

WARNING: This script will DELETE ALL existing data in the database.
Only use in development or when you're certain you want to start fresh.

Usage:
    python reset_db.py

Requirements:
    - Django environment properly configured
    - Database connection established
    - All migrations applied
"""

import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model
from users.models import UserProfile

User = get_user_model()

def reset_database():
    """Flush the database, removing all data.
    
    This function completely clears the database using Django's
    flush command. All tables are emptied and reset to their
    initial state.
    """
    print("Flushing database...")
    call_command('flush', '--no-input')
    print("Database flushed successfully!")

def create_superuser():
    """Create a superuser with predefined credentials.
    
    Creates a default administrator account that can be used
    to access the Django admin interface and manage the application.
    
    Default credentials:
    - Username: admin
    - Email: admin@example.com
    - Password: admin123
    """
    username = 'admin'
    email = 'admin@example.com'
    password = 'admin123'
    
    print(f"Creating superuser '{username}'...")
    
    # Check if user already exists
    if User.objects.filter(username=username).exists():
        print(f"Superuser '{username}' already exists.")
        return
    
    # Create superuser
    try:
        superuser = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            current_role='Administrator',
            experience_level='senior'
        )
        
        # Create related UserProfile
        UserProfile.objects.get_or_create(user=superuser)
        
        print(f"Superuser '{username}' created successfully!")
        print(f"Email: {email}")
        print(f"Password: {password}")
    except Exception as e:
        print(f"Error creating superuser: {str(e)}")

def populate_career_data():
    """Populate career roles, skills, and other initial data.
    
    Loads sample data into the database to provide a working
    foundation for the application. This includes career roles,
    skill categories, and other reference data.
    """
    print("Populating career data...")
    try:
        call_command('populate_career_data')
        print("Career data populated successfully!")
    except Exception as e:
        print(f"Error populating career data: {str(e)}")

def main():
    """Run the complete reset and setup process.
    
    Executes all setup functions in the correct order to ensure
    a properly initialized application. Provides clear feedback
    throughout the process and final instructions for next steps.
    """
    print("=== CAREER NEXUS DATABASE RESET AND SETUP ===")
    print("This will completely reset your database and create fresh data.")
    print("Make sure you have backed up any important data before proceeding.\n")
    
    reset_database()
    create_superuser()
    populate_career_data()
    
    print("\n=== SETUP COMPLETE ===")
    print("Your database has been reset and initialized successfully!")
    print("\nNext steps:")
    print("1. Start the Django development server: python manage.py runserver")
    print("2. Start the Celery worker: celery -A config.celery.app worker --loglevel=INFO")
    print("3. Start Redis: redis-server")
    print("4. Access the admin interface at: http://localhost:8000/admin/")
    print("\nDefault admin credentials:")
    print("  Username: admin")
    print("  Password: admin123")
    print("\nRemember to change the default password in production!")

if __name__ == "__main__":
    main() 