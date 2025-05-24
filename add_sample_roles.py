import os
import django
import sys

# Setup Django environment
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from skills.models import CareerRole, RoleSkill

def create_role(name, description, category, skills_data):
    """
    Create a career role and its required skills.
    
    Args:
        name: Role name
        description: Role description
        category: Role category
        skills_data: List of dicts with 'name' and 'importance' keys
    """
    # Create or update the role
    role, created = CareerRole.objects.get_or_create(
        name=name,
        defaults={
            'description': description,
            'category': category
        }
    )
    
    if not created:
        # Update existing role
        role.description = description
        role.category = category
        role.save()
        
        # Remove existing skills to avoid duplicates
        RoleSkill.objects.filter(role=role).delete()
    
    # Create required skills
    for skill_data in skills_data:
        RoleSkill.objects.create(
            role=role,
            skill_name=skill_data['name'],
            importance=skill_data['importance']
        )
    
    print(f"{'Created' if created else 'Updated'} role: {name}")
    return role

def add_sample_roles():
    """Add sample career roles with required skills."""
    # Software Engineering roles
    create_role(
        name="Frontend Developer",
        description="Specializes in developing user interfaces and experiences for web applications.",
        category="Software Development",
        skills_data=[
            {'name': 'HTML', 'importance': 'essential'},
            {'name': 'CSS', 'importance': 'essential'},
            {'name': 'JavaScript', 'importance': 'essential'},
            {'name': 'React', 'importance': 'important'},
            {'name': 'Responsive Design', 'importance': 'important'},
            {'name': 'TypeScript', 'importance': 'nice_to_have'},
            {'name': 'UI/UX Design', 'importance': 'nice_to_have'},
            {'name': 'Jest', 'importance': 'nice_to_have'}
        ]
    )
    
    create_role(
        name="Backend Developer",
        description="Develops server-side logic, databases, and application architecture.",
        category="Software Development",
        skills_data=[
            {'name': 'Python', 'importance': 'essential'},
            {'name': 'SQL', 'importance': 'essential'},
            {'name': 'API Development', 'importance': 'essential'},
            {'name': 'Django', 'importance': 'important'},
            {'name': 'Database Design', 'importance': 'important'},
            {'name': 'REST APIs', 'importance': 'important'},
            {'name': 'Docker', 'importance': 'nice_to_have'},
            {'name': 'AWS', 'importance': 'nice_to_have'}
        ]
    )
    
    create_role(
        name="Full Stack Developer",
        description="Develops both client and server software, working with databases, APIs, and user interfaces.",
        category="Software Development",
        skills_data=[
            {'name': 'JavaScript', 'importance': 'essential'},
            {'name': 'Python', 'importance': 'essential'},
            {'name': 'React', 'importance': 'important'},
            {'name': 'Node.js', 'importance': 'important'},
            {'name': 'SQL', 'importance': 'important'},
            {'name': 'HTML', 'importance': 'essential'},
            {'name': 'CSS', 'importance': 'essential'},
            {'name': 'Git', 'importance': 'essential'},
            {'name': 'Docker', 'importance': 'nice_to_have'},
            {'name': 'CI/CD', 'importance': 'nice_to_have'}
        ]
    )
    
    # Data Science roles
    create_role(
        name="Data Scientist",
        description="Analyzes and interprets complex data to help organizations make better decisions.",
        category="Data Science",
        skills_data=[
            {'name': 'Python', 'importance': 'essential'},
            {'name': 'Machine Learning', 'importance': 'essential'},
            {'name': 'Statistics', 'importance': 'essential'},
            {'name': 'SQL', 'importance': 'important'},
            {'name': 'Data Visualization', 'importance': 'important'},
            {'name': 'Pandas', 'importance': 'important'},
            {'name': 'TensorFlow', 'importance': 'nice_to_have'},
            {'name': 'PyTorch', 'importance': 'nice_to_have'},
            {'name': 'Big Data', 'importance': 'nice_to_have'}
        ]
    )
    
    create_role(
        name="Data Engineer",
        description="Develops, constructs, tests and maintains data architectures.",
        category="Data Science",
        skills_data=[
            {'name': 'SQL', 'importance': 'essential'},
            {'name': 'Python', 'importance': 'essential'},
            {'name': 'ETL', 'importance': 'essential'},
            {'name': 'Hadoop', 'importance': 'important'},
            {'name': 'Spark', 'importance': 'important'},
            {'name': 'Data Warehousing', 'importance': 'important'},
            {'name': 'AWS', 'importance': 'nice_to_have'},
            {'name': 'Airflow', 'importance': 'nice_to_have'}
        ]
    )
    
    # Design roles
    create_role(
        name="UX Designer",
        description="Focuses on the interaction between users and products to create meaningful experiences.",
        category="Design",
        skills_data=[
            {'name': 'User Research', 'importance': 'essential'},
            {'name': 'Wireframing', 'importance': 'essential'},
            {'name': 'Prototyping', 'importance': 'essential'},
            {'name': 'Figma', 'importance': 'important'},
            {'name': 'Adobe XD', 'importance': 'important'},
            {'name': 'Information Architecture', 'importance': 'important'},
            {'name': 'HTML/CSS', 'importance': 'nice_to_have'},
            {'name': 'JavaScript', 'importance': 'nice_to_have'}
        ]
    )
    
    create_role(
        name="Product Manager",
        description="Identifies customer needs and business objectives to guide product development.",
        category="Product",
        skills_data=[
            {'name': 'Product Strategy', 'importance': 'essential'},
            {'name': 'User Research', 'importance': 'essential'},
            {'name': 'Market Analysis', 'importance': 'essential'},
            {'name': 'Agile Methodologies', 'importance': 'important'},
            {'name': 'A/B Testing', 'importance': 'important'},
            {'name': 'Data Analysis', 'importance': 'important'},
            {'name': 'Technical Understanding', 'importance': 'nice_to_have'},
            {'name': 'UI/UX Design', 'importance': 'nice_to_have'}
        ]
    )

if __name__ == '__main__':
    add_sample_roles()
    print("Sample roles added successfully!") 