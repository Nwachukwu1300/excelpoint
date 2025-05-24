import os
import django
import sys

# Setup Django environment
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from skills.models import Skill, UserSkill

User = get_user_model()

def add_skills_to_user(username, skills_list):
    """
    Add sample skills to a user.
    
    Args:
        username: Username to add skills to
        skills_list: List of skill names to add
    """
    try:
        user = User.objects.get(username=username)
        print(f"Found user: {user.username}")
        
        skills_added = 0
        
        for skill_name in skills_list:
            # Check if user already has this skill
            existing_skill = UserSkill.objects.filter(
                user=user,
                skill_name__iexact=skill_name
            ).exists()
            
            if not existing_skill:
                # Create the UserSkill for this user
                UserSkill.objects.create(
                    user=user,
                    skill_name=skill_name
                )
                skills_added += 1
                print(f"Added skill: {skill_name}")
            else:
                print(f"Skill already exists: {skill_name}")
                
        # Also add these skills to the ManyToMany relationship for compatibility
        for skill_name in skills_list:
            # Check if skill exists as a Skill object
            skill, created = Skill.objects.get_or_create(
                name=skill_name,
                defaults={'category': 'added-via-script'}
            )
            
            # Add to M2M if not already there
            if skill not in user.skills.all():
                user.skills.add(skill)
                
        print(f"Added {skills_added} new skills to {user.username}")
        return skills_added
                
    except User.DoesNotExist:
        print(f"Error: User '{username}' not found")
        return 0

def main():
    # Get the username from command line args or use a default
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        # List users and prompt for selection if no username provided
        users = User.objects.all()
        
        if not users:
            print("No users found in the database.")
            return
            
        print("Available users:")
        for i, user in enumerate(users):
            print(f"{i+1}. {user.username}")
            
        while True:
            try:
                choice = int(input("\nSelect a user (number): ")) - 1
                if 0 <= choice < len(users):
                    username = users[choice].username
                    break
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a number.")
    
    # Common skills that should match with some of our career roles
    skills = [
        # Programming
        'Python', 
        'JavaScript',
        'HTML',
        'CSS',
        
        # Data skills
        'SQL',
        'Data Analysis',
        
        # Soft skills
        'Project Management',
        'Communication',
        
        # Design skills
        'UI/UX Design',
        
        # Cloud
        'AWS',
        
        # Development tools
        'Git'
    ]
    
    added = add_skills_to_user(username, skills)
    if added > 0:
        print(f"\nSuccessfully added skills to user '{username}'.")
        print("Now the recommended roles should show higher match percentages.")
    else:
        print(f"\nNo new skills were added to user '{username}'.")

if __name__ == '__main__':
    main() 