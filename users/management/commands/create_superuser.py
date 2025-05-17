import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from users.models import UserProfile

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a superuser with predefined credentials'

    def handle(self, *args, **options):
        username = 'admin'
        email = 'admin@example.com'
        password = 'admin123'
        
        try:
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                self.stdout.write(self.style.WARNING(f'Superuser "{username}" already exists.'))
                return
                
            # Create superuser
            superuser = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                current_role='Administrator',
                experience_level='senior'
            )
            
            # Create or update related UserProfile
            try:
                UserProfile.objects.get_or_create(user=superuser)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error creating user profile: {str(e)}'))
            
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" created successfully!'))
            self.stdout.write(self.style.SUCCESS(f'Email: {email}'))
            self.stdout.write(self.style.SUCCESS(f'Password: {password}'))
            
        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Unexpected error: {str(e)}')) 