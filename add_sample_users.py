import os
import sys
import django
import random
from datetime import timedelta
from django.utils import timezone

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Import Django models
from django.contrib.auth import get_user_model
from users.models import UserProfile, UserEducation
from learning.models import Course, CourseProgress

User = get_user_model()

# Sample data
first_names = [
    'Emma', 'Olivia', 'Ava', 'Isabella', 'Sophia', 'Mia', 'Charlotte', 'Amelia', 'Harper', 'Evelyn',
    'Liam', 'Noah', 'William', 'James', 'Oliver', 'Benjamin', 'Elijah', 'Lucas', 'Mason', 'Logan',
    'Aiden', 'Jackson', 'Chloe', 'Madison', 'Elizabeth', 'Ella', 'Emily', 'Avery', 'Sofia', 'Camila',
    'Aria', 'Scarlett', 'Victoria', 'Layla', 'Michael', 'Alexander', 'Ethan', 'Daniel', 'Matthew', 'Jacob',
    'Maya', 'Nora', 'Riley', 'Zoe', 'David', 'Joseph', 'Samuel', 'Henry', 'Owen', 'Wyatt',
    'John', 'Jack', 'Luke', 'Jayden', 'Dylan', 'Oscar', 'Gabriel', 'Julian', 'Mateo', 'Leo',
    'Lily', 'Hannah', 'Addison', 'Eleanor', 'Aubrey', 'Ellie', 'Stella', 'Natalie', 'Zoey', 'Leah',
]

last_names = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez',
    'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin',
    'Lee', 'Perez', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson',
    'Walker', 'Young', 'Allen', 'King', 'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill', 'Flores',
    'Green', 'Adams', 'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell', 'Mitchell', 'Carter', 'Roberts',
    'Patel', 'Kim', 'Chen', 'Wang', 'Singh', 'Li', 'Zhang', 'Wu', 'Liu', 'Gupta',
    'Ali', 'Murphy', 'O\'Connor', 'Kelly', 'Ryan', 'Kennedy', 'Quinn', 'Sullivan', 'O\'Brien', 'McLaughlin',
]

education_institutions = [
    'Stanford University', 'Harvard University', 'MIT', 'University of California, Berkeley',
    'Princeton University', 'New York University', 'University of Michigan', 'Yale University',
    'University of Chicago', 'Columbia University', 'University of Washington', 'Georgia Tech',
    'Cornell University', 'Duke University', 'University of Pennsylvania', 'Northwestern University',
    'Carnegie Mellon University', 'University of Texas at Austin', 'Boston University', 'Purdue University',
    'University of Illinois Urbana-Champaign', 'California Institute of Technology', 'UCLA',
    'University of Wisconsin-Madison', 'University of Florida', 'Ohio State University',
    'Johns Hopkins University', 'University of North Carolina at Chapel Hill'
]

degrees = [
    'Bachelor of Science in Computer Science', 'Bachelor of Arts in English',
    'Bachelor of Science in Electrical Engineering', 'Bachelor of Business Administration',
    'Master of Business Administration', 'Master of Science in Data Science',
    'Master of Arts in Psychology', 'Bachelor of Science in Mathematics',
    'Bachelor of Science in Biology', 'Master of Engineering',
    'PhD in Computer Science', 'Master of Science in Artificial Intelligence',
    'Bachelor of Arts in Communication', 'Bachelor of Science in Information Technology',
    'Master of Science in Cybersecurity', 'Bachelor of Arts in Economics',
    'Bachelor of Science in Physics', 'Master of Science in Machine Learning',
    'Bachelor of Science in Software Engineering', 'Master of Arts in Digital Marketing'
]

def create_users(num_users=10):
    """Create sample users with real names and assign them courses"""
    courses = list(Course.objects.all())
    
    if not courses:
        print("No courses found in the database!")
        return
    
    users_created = 0
    statuses = ['not_started', 'in_progress', 'completed', 'paused']
    
    print(f"Creating {num_users} sample users...")
    
    for i in range(num_users):
        # Create user with unique name
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        username = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}"
        email = f"{username}@example.com"
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            username = f"{first_name.lower()}.{last_name.lower()}{random.randint(1000, 9999)}"
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password='Test123',
            first_name=first_name,
            last_name=last_name
        )
        
        # Update user profile
        profile_bio = f"Professional with interests in {', '.join(random.sample(['web development', 'data science', 'machine learning', 'cybersecurity', 'UI/UX design', 'mobile development', 'cloud computing', 'DevOps'], k=random.randint(2, 4)))}."
        
        # Get or create profile
        try:
            profile = UserProfile.objects.get(user=user)
            profile.bio = profile_bio
            profile.save()
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(
                user=user,
                bio=profile_bio
            )
        
        # Create education
        num_education = random.randint(1, 2)
        for _ in range(num_education):
            institution = random.choice(education_institutions)
            degree = random.choice(degrees)
            graduation_year = str(random.randint(2010, 2023))
            
            UserEducation.objects.create(
                user=user,
                institution=institution,
                degree=degree,
                field_of_study=degree.split(' in ')[-1] if ' in ' in degree else '',
                graduation_date=graduation_year,
                gpa=f"{random.uniform(3.0, 4.0):.2f}"
            )
        
        # Enroll in random courses
        num_courses = random.randint(3, 8)
        user_courses = random.sample(courses, min(num_courses, len(courses)))
        
        for course in user_courses:
            status = random.choice(statuses)
            date_started = None
            date_completed = None
            
            if status in ['in_progress', 'completed', 'paused']:
                date_started = timezone.now() - timedelta(days=random.randint(10, 90))
                
            if status == 'completed':
                date_completed = date_started + timedelta(days=random.randint(10, 60))
            
            progress = CourseProgress.objects.create(
                user=user,
                course=course,
                status=status,
                date_started=date_started,
                date_completed=date_completed,
                estimated_hours_spent=random.randint(1, 40)
            )
            
            # Add a note to the progress
            from learning.models import CourseProgressNote
            CourseProgressNote.objects.create(
                progress=progress,
                note=f"{'Really enjoying this course!' if random.random() > 0.5 else 'Learning a lot from this material.'}"
            )
        
        users_created += 1
        print(f"Created user: {user.username} ({user.first_name} {user.last_name})")
    
    print(f"Successfully created {users_created} users!")

if __name__ == '__main__':
    # Get number of users to create from command line arguments or default to 10
    num_users = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    create_users(num_users) 