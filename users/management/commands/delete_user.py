from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Deletes a user by username'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the user to delete')
        parser.add_argument('--force', action='store_true', help='Force deletion without confirmation')

    def handle(self, *args, **options):
        username = options['username']
        force = options['force']
        
        try:
            user = User.objects.get(username=username)
            
            if not force:
                self.stdout.write(f"User found: {user.username} (ID: {user.id})")
                confirm = input('Are you sure you want to delete this user? [y/N]: ')
                if confirm.lower() != 'y':
                    self.stdout.write(self.style.WARNING('User deletion cancelled.'))
                    return
            
            with transaction.atomic():
                # Delete any related objects that might prevent user deletion
                # This depends on your model relationships
                
                # Delete the user
                user.delete()
                
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted user: {username}'))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User with username "{username}" does not exist.')) 