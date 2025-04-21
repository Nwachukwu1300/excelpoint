from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from skills.models import Skill

User = get_user_model()

class Command(BaseCommand):
    help = 'Assigns user ownership to skills that currently have no owner'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int, help='User ID to assign skills to')
        parser.add_argument('--dry-run', action='store_true', help='Simulate without making changes')

    def handle(self, *args, **options):
        user_id = options['user_id']
        dry_run = options['dry_run']
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User with ID {user_id} does not exist'))
            return
            
        # Get all skills with no user
        orphaned_skills = Skill.objects.filter(user__isnull=True)
        count = orphaned_skills.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No orphaned skills found'))
            return
            
        self.stdout.write(f'Found {count} skills with no user assigned')
        
        if dry_run:
            self.stdout.write('Dry run - no changes will be made')
            for skill in orphaned_skills:
                self.stdout.write(f'  Would assign skill "{skill.name}" to {user.username}')
            return
            
        # Assign all orphaned skills to the specified user
        for skill in orphaned_skills:
            skill.user = user
            skill.save()
            
            # Also add to M2M relationship if not already there
            if skill not in user.skills.all():
                user.skills.add(skill)
                
            self.stdout.write(f'  Assigned skill "{skill.name}" to {user.username}')
            
        self.stdout.write(self.style.SUCCESS(f'Successfully assigned {count} skills to {user.username}')) 