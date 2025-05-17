#!/usr/bin/env python
"""
Career Nexus Database Reset and Setup Script
--------------------------------------------
This script resets the database and sets up initial data for a fresh installation.
Steps:
1. Flush the database
2. Create a superuser
3. Load initial data (career roles, skills)
"""
import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model
from users.models import UserProfile

User = get_user_model()

def reset_database():
    """Flush the database, removing all data."""
    print("Flushing database...")
    call_command('flush', '--no-input')
    print("Database flushed successfully!")

def create_superuser():
    """Create a superuser with predefined credentials."""
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
    """Populate career roles, skills, and other initial data."""
    print("Populating career data...")
    try:
        call_command('populate_career_data')
        print("Career data populated successfully!")
    except Exception as e:
        print(f"Error populating career data: {str(e)}")

def main():
    """Run the complete reset and setup process."""
    print("=== CAREER NEXUS DATABASE RESET AND SETUP ===")
    
    reset_database()
    create_superuser()
    populate_career_data()
    
    print("\nSetup complete! You can now start the application.")
    print("Login with:")
    print("  Username: admin")
    print("  Password: admin123")

if __name__ == "__main__":
    main() 