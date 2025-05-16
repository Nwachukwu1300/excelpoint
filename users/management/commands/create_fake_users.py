import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import UserProfile, UserEducation, UserCertification, UserAchievement as UserProfessionalAchievement
from skills.models import Skill, CareerRole, RoleSkill, Course, UserSkill
from learning.models import CourseProgress, LearningResource, SavedResource, Achievement, UserAchievement as UserLearningAchievement
from jobs.models import Job

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates fake users with complete profiles'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=10, help='Number of fake users to create')

    def handle(self, *args, **options):
        count = options['count']
        self.stdout.write(f"Creating {count} fake users with complete profiles...")
        
        # Make sure we have some career roles and skills
        self.ensure_career_roles_exist()
        self.ensure_skills_exist()
        self.ensure_courses_exist()
        
        # Generate users
        for i in range(count):
            self.create_fake_user(i)
            
        self.stdout.write(self.style.SUCCESS(f'Successfully created {count} fake users'))

    def ensure_career_roles_exist(self):
        """Ensure we have some career roles to work with"""
        career_roles = [
            ('Software Engineer', 'Development', 'Develops software applications using programming languages and frameworks'),
            ('Data Scientist', 'Data Science', 'Analyzes and interprets complex data to help make business decisions'),
            ('UX/UI Designer', 'Design', 'Creates user-friendly interfaces and experiences for websites and applications'),
            ('Product Manager', 'Management', 'Oversees the development and marketing of products'),
            ('DevOps Engineer', 'Operations', 'Manages the infrastructure and deployment of software'),
            ('Machine Learning Engineer', 'AI/ML', 'Builds machine learning models and implements them in applications'),
            ('Frontend Developer', 'Development', 'Specializes in building the user-facing parts of websites and applications'),
            ('Backend Developer', 'Development', 'Focuses on the server-side logic and databases of applications')
        ]
        
        for name, category, description in career_roles:
            CareerRole.objects.get_or_create(
                name=name,
                defaults={
                    'category': category,
                    'description': description
                }
            )

    def ensure_skills_exist(self):
        """Ensure we have some skills to work with"""
        skills_data = [
            # Technical skills
            ('Python', 'Technical', 'Programming language known for its readability and versatility'),
            ('JavaScript', 'Technical', 'Programming language for web development'),
            ('React', 'Technical', 'JavaScript library for building user interfaces'),
            ('SQL', 'Technical', 'Language for managing and querying databases'),
            ('Docker', 'Technical', 'Platform for developing, shipping, and running applications in containers'),
            ('Kubernetes', 'Technical', 'Container orchestration system'),
            ('AWS', 'Technical', 'Cloud computing platform'),
            ('Machine Learning', 'Technical', 'Field of AI that enables systems to learn from data'),
            ('Django', 'Technical', 'Python web framework'),
            ('Node.js', 'Technical', 'JavaScript runtime environment'),
            
            # Soft skills
            ('Communication', 'Soft Skills', 'Ability to convey information effectively'),
            ('Leadership', 'Soft Skills', 'Ability to guide and motivate a team'),
            ('Problem Solving', 'Soft Skills', 'Ability to find solutions to complex issues'),
            ('Critical Thinking', 'Soft Skills', 'Analytical thinking to evaluate situations objectively'),
            ('Time Management', 'Soft Skills', 'Ability to organize and prioritize tasks effectively')
        ]
        
        for name, category, description in skills_data:
            Skill.objects.get_or_create(
                name=name,
                defaults={
                    'category': category,
                    'description': description
                }
            )
        
        # Associate skills with career roles
        self.associate_skills_with_roles()

    def associate_skills_with_roles(self):
        """Associate skills with career roles"""
        role_skills = {
            'Software Engineer': ['Python', 'JavaScript', 'Problem Solving', 'SQL', 'Docker'],
            'Data Scientist': ['Python', 'Machine Learning', 'SQL', 'Critical Thinking'],
            'UX/UI Designer': ['JavaScript', 'React', 'Communication', 'Critical Thinking'],
            'Product Manager': ['Communication', 'Leadership', 'Problem Solving', 'Time Management'],
            'DevOps Engineer': ['Docker', 'Kubernetes', 'AWS', 'Problem Solving'],
            'Machine Learning Engineer': ['Python', 'Machine Learning', 'AWS', 'Critical Thinking'],
            'Frontend Developer': ['JavaScript', 'React', 'Communication', 'Problem Solving'],
            'Backend Developer': ['Python', 'Django', 'SQL', 'Docker', 'AWS']
        }
        
        importance_levels = ['essential', 'important', 'nice_to_have']
        
        for role_name, skill_names in role_skills.items():
            try:
                role = CareerRole.objects.get(name=role_name)
                for skill_name in skill_names:
                    importance = random.choice(importance_levels)
                    RoleSkill.objects.get_or_create(
                        role=role,
                        skill_name=skill_name,
                        defaults={'importance': importance}
                    )
            except CareerRole.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Career role {role_name} does not exist'))

    def ensure_courses_exist(self):
        """Ensure we have some courses to work with"""
        courses_data = [
            {
                'title': 'Introduction to Python Programming',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/learn/python',
                'description': 'Learn the basics of Python programming language',
                'difficulty': 'beginner',
                'duration': '4 weeks',
                'is_free': False,
                'skills': ['Python', 'Problem Solving']
            },
            {
                'title': 'Advanced JavaScript Concepts',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/advanced-javascript',
                'description': 'Deep dive into JavaScript concepts like closures, prototypes, and async',
                'difficulty': 'advanced',
                'duration': '20 hours',
                'is_free': False,
                'skills': ['JavaScript', 'Critical Thinking']
            },
            {
                'title': 'React for Beginners',
                'provider': 'Frontend Masters',
                'url': 'https://frontendmasters.com/courses/react',
                'description': 'Learn React from the ground up',
                'difficulty': 'beginner',
                'duration': '12 hours',
                'is_free': False,
                'skills': ['React', 'JavaScript']
            },
            {
                'title': 'SQL Essentials',
                'provider': 'Khan Academy',
                'url': 'https://www.khanacademy.org/computing/computer-programming/sql',
                'description': 'Learn the fundamentals of SQL',
                'difficulty': 'beginner',
                'duration': '10 hours',
                'is_free': True,
                'skills': ['SQL', 'Problem Solving']
            },
            {
                'title': 'Docker and Kubernetes: The Complete Guide',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/docker-and-kubernetes',
                'description': 'Master containerization with Docker and orchestration with Kubernetes',
                'difficulty': 'intermediate',
                'duration': '24 hours',
                'is_free': False,
                'skills': ['Docker', 'Kubernetes']
            },
            {
                'title': 'AWS Certified Solutions Architect',
                'provider': 'A Cloud Guru',
                'url': 'https://acloud.guru/learn/aws-certified-solutions-architect-associate',
                'description': 'Preparation for the AWS Solutions Architect certification',
                'difficulty': 'intermediate',
                'duration': '40 hours',
                'is_free': False,
                'skills': ['AWS', 'Problem Solving']
            },
            {
                'title': 'Machine Learning A-Z',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/machinelearning',
                'description': 'Hands-on Python & R in data science and machine learning',
                'difficulty': 'intermediate',
                'duration': '44 hours',
                'is_free': False,
                'skills': ['Python', 'Machine Learning']
            },
            {
                'title': 'Django for Beginners',
                'provider': 'Real Python',
                'url': 'https://realpython.com/django-for-beginners',
                'description': 'Build web applications with Django and Python',
                'difficulty': 'beginner',
                'duration': '15 hours',
                'is_free': False,
                'skills': ['Python', 'Django', 'SQL']
            }
        ]
        
        for course_data in courses_data:
            skills = course_data.pop('skills')
            course, created = Course.objects.get_or_create(
                title=course_data['title'],
                defaults=course_data
            )
            
            if created:
                for skill_name in skills:
                    try:
                        skill = Skill.objects.get(name=skill_name)
                        course.skills_taught.add(skill)
                    except Skill.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f'Skill {skill_name} does not exist'))

    def create_fake_user(self, index):
        """Create a single fake user with complete profile"""
        # Generate user data
        first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Riley", "Casey", "Quinn", "Jamie", "Avery", "Sam"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
        experience_levels = ["entry", "mid", "senior"]
        
        username = f"user{index+1}"
        email = f"user{index+1}@example.com"
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        experience_level = random.choice(experience_levels)
        
        # Check if user already exists
        try:
            user = User.objects.get(username=username)
            self.stdout.write(self.style.WARNING(f'User {username} already exists, skipping creation'))
            return user
        except User.DoesNotExist:
            # Create the user
            user = User.objects.create_user(
                username=username,
                email=email,
                password='password123',
                first_name=first_name,
                last_name=last_name,
                experience_level=experience_level
            )
        
        # Set current role and dream job
        roles = list(CareerRole.objects.all())
        if roles:
            user.current_role = random.choice(roles).name
            user.dream_job = random.choice(roles)
            user.save()
        
        # Create UserProfile if it doesn't exist
        if not hasattr(user, 'profile'):
            UserProfile.objects.create(
                user=user,
                bio=f"I am {first_name} {last_name}, a {experience_level}-level professional passionate about {user.current_role if user.current_role else 'technology'}.",
                linkedin_profile=f"https://linkedin.com/in/{first_name.lower()}-{last_name.lower()}-{index+1}",
                github_profile=f"https://github.com/{first_name.lower()}{last_name.lower()}{index+1}"
            )
        
        # Add user skills
        self.add_user_skills(user)
        
        # Add education
        self.add_user_education(user)
        
        # Add certifications
        self.add_user_certifications(user)
        
        # Add achievements
        self.add_user_achievements(user)
        
        # Add course progress
        self.add_course_progress(user)
        
        # Add saved resources
        self.add_saved_resources(user)
        
        return user
        
    def add_user_skills(self, user):
        """Add random skills to the user"""
        skills = list(Skill.objects.all())
        num_skills = random.randint(3, 8)
        selected_skills = random.sample(skills, min(num_skills, len(skills)))
        
        for skill in selected_skills:
            UserSkill.objects.get_or_create(
                user=user,
                skill_name=skill.name,
                defaults={'is_verified': random.choice([True, False])}
            )
            
            user.skills.add(skill)
        
    def add_user_education(self, user):
        """Add random education records to the user"""
        institutions = [
            "Stanford University", "MIT", "Harvard University", "University of California", 
            "Georgia Tech", "Cornell University", "Carnegie Mellon University"
        ]
        degrees = [
            "Bachelor of Science", "Master of Science", "Bachelor of Arts", 
            "Master of Arts", "PhD", "Associate's Degree"
        ]
        fields = [
            "Computer Science", "Data Science", "Information Technology", 
            "Software Engineering", "UX Design", "Business Administration"
        ]
        
        # Check if user already has education records
        if user.education.exists():
            self.stdout.write(self.style.WARNING(f'User {user.username} already has education records, skipping'))
            return
            
        num_records = random.randint(1, 3)
        for i in range(num_records):
            grad_year = datetime.now().year - random.randint(0, 15)
            UserEducation.objects.create(
                user=user,
                institution=random.choice(institutions),
                degree=random.choice(degrees),
                field_of_study=random.choice(fields),
                graduation_date=str(grad_year),
                gpa=f"{random.uniform(2.5, 4.0):.2f}",
                additional_info="Dean's List" if random.choice([True, False]) else ""
            )
    
    def add_user_certifications(self, user):
        """Add random certifications to the user"""
        # Check if user already has certifications
        if user.certifications.exists():
            self.stdout.write(self.style.WARNING(f'User {user.username} already has certifications, skipping'))
            return
            
        certifications = [
            ("AWS Certified Solutions Architect", "Amazon Web Services"),
            ("Google Cloud Professional Data Engineer", "Google Cloud"),
            ("Certified Kubernetes Administrator", "Cloud Native Computing Foundation"),
            ("Microsoft Certified: Azure Developer Associate", "Microsoft"),
            ("Certified Scrum Master", "Scrum Alliance"),
            ("Certified Python Developer", "Python Institute"),
            ("TensorFlow Developer Certificate", "Google"),
            ("Certified Ethical Hacker", "EC-Council")
        ]
        
        num_certs = random.randint(0, 3)
        selected_certs = random.sample(certifications, min(num_certs, len(certifications)))
        
        for name, issuer in selected_certs:
            earned_year = datetime.now().year - random.randint(0, 5)
            expiration_year = earned_year + random.randint(2, 5)
            
            UserCertification.objects.create(
                user=user,
                name=name,
                issuer=issuer,
                date_earned=f"{earned_year}-{random.randint(1, 12)}",
                expiration_date=f"{expiration_year}-{random.randint(1, 12)}",
                credential_id=f"CERT-{random.randint(10000, 99999)}",
                credential_url=f"https://{issuer.lower().replace(' ', '')}.com/verify/{random.randint(100000, 999999)}"
            )
    
    def add_user_achievements(self, user):
        """Add random achievements to the user"""
        # Check if user already has achievements
        if user.user_achievements.exists():
            self.stdout.write(self.style.WARNING(f'User {user.username} already has achievements, skipping'))
            return
            
        achievement_types = ['award', 'scholarship', 'honor', 'publication', 'patent', 'grant', 'general']
        achievement_titles = [
            "Employee of the Month", "Innovation Award", "Research Grant",
            "Published Paper in Tech Journal", "Open Source Contribution Award",
            "Hackathon Winner", "Patent for Technology Innovation"
        ]
        organizations = [
            "Google", "Microsoft", "IBM", "Tech Conference", "University Research Department",
            "Open Source Foundation", "Industry Association"
        ]
        
        num_achievements = random.randint(0, 3)
        
        for i in range(num_achievements):
            achievement_type = random.choice(achievement_types)
            year_received = datetime.now().year - random.randint(0, 10)
            
            UserProfessionalAchievement.objects.create(
                user=user,
                title=random.choice(achievement_titles),
                type=achievement_type,
                organization=random.choice(organizations),
                date_received=f"{year_received}-{random.randint(1, 12)}",
                description=f"Recognized for exceptional work in {random.choice(['innovation', 'leadership', 'technical expertise', 'research'])}"
            )
        
        # Also add some learning achievements if they exist
        self.add_learning_achievements(user)
    
    def add_learning_achievements(self, user):
        """Add learning achievements to the user"""
        # First check if we have any achievements defined
        achievements = Achievement.objects.all()
        if not achievements.exists():
            # Create some achievements
            achievement_data = [
                {
                    'name': 'Course Starter',
                    'description': 'Started your first course',
                    'icon': '🏁',
                    'requirement_type': 'courses_started',
                    'requirement_value': 1
                },
                {
                    'name': 'Course Completer',
                    'description': 'Completed your first course',
                    'icon': '🎓',
                    'requirement_type': 'courses_completed',
                    'requirement_value': 1
                },
                {
                    'name': 'Learning Enthusiast',
                    'description': 'Completed 5 courses',
                    'icon': '🔥',
                    'requirement_type': 'courses_completed',
                    'requirement_value': 5
                },
                {
                    'name': 'Streak Starter',
                    'description': 'Maintained a 3-day learning streak',
                    'icon': '📆',
                    'requirement_type': 'streak',
                    'requirement_value': 3
                }
            ]
            
            for data in achievement_data:
                Achievement.objects.get_or_create(
                    name=data['name'],
                    defaults=data
                )
            
            achievements = Achievement.objects.all()
        
        # Now assign some random achievements to the user
        if not hasattr(user, 'achievements') or not user.achievements.exists():
            num_achievements = random.randint(0, min(3, achievements.count()))
            selected_achievements = random.sample(list(achievements), num_achievements)
            
            for achievement in selected_achievements:
                UserLearningAchievement.objects.create(
                    user=user,
                    achievement=achievement,
                    date_earned=datetime.now() - timedelta(days=random.randint(1, 90))
                )
    
    def add_course_progress(self, user):
        """Add random course progress records to the user"""
        # Check if user already has course progress
        if hasattr(user, 'course_progress') and user.course_progress.exists():
            self.stdout.write(self.style.WARNING(f'User {user.username} already has course progress, skipping'))
            return
            
        courses = list(Course.objects.all())
        if not courses:
            return
            
        num_courses = random.randint(1, min(5, len(courses)))
        selected_courses = random.sample(courses, num_courses)
        
        statuses = ['not_started', 'in_progress', 'completed', 'paused']
        
        for course in selected_courses:
            status = random.choice(statuses)
            now = datetime.now()
            
            date_started = None
            date_completed = None
            
            if status in ['in_progress', 'completed', 'paused']:
                date_started = now - timedelta(days=random.randint(30, 365))
                
            if status == 'completed':
                date_completed = date_started + timedelta(days=random.randint(7, 180))
            
            CourseProgress.objects.create(
                user=user,
                course=course,
                status=status,
                date_started=date_started,
                date_completed=date_completed,
                estimated_hours_spent=random.randint(1, 50),
                notes=f"{'Really enjoying this course!' if random.choice([True, False]) else 'Need to review chapter 3 again.'}"
            )
    
    def add_saved_resources(self, user):
        """Add random saved resources to the user"""
        # Check if user already has saved resources
        if hasattr(user, 'saved_resources') and user.saved_resources.exists():
            self.stdout.write(self.style.WARNING(f'User {user.username} already has saved resources, skipping'))
            return
            
        resource_types = ['article', 'video', 'book', 'podcast', 'documentation', 'other']
        resource_titles = [
            "10 Best Practices for Clean Code", 
            "Introduction to Machine Learning",
            "Understanding Microservices Architecture",
            "DevOps Fundamentals",
            "The Art of UX Design",
            "Effective Time Management for Developers",
            "Cloud Computing Essentials"
        ]
        resource_urls = [
            "https://medium.com/article/clean-code-best-practices",
            "https://youtube.com/watch?v=intro-to-ml",
            "https://techbooks.com/microservices-architecture",
            "https://devopspodcast.com/fundamentals-episode",
            "https://uxdesign.cc/art-of-ux",
            "https://dev.to/time-management",
            "https://cloud-essentials.com/guide"
        ]
        
        num_resources = random.randint(0, 5)
        
        for i in range(num_resources):
            idx = random.randint(0, len(resource_titles) - 1)
            resource_type = random.choice(resource_types)
            SavedResource.objects.create(
                user=user,
                title=resource_titles[idx],
                url=resource_urls[idx],
                description=f"A great resource for learning about {resource_titles[idx].lower()}",
                resource_type=resource_type,
                tags=','.join(random.sample(['programming', 'career', 'technical', 'soft skills', 'development'], random.randint(1, 3))),
                notes="Need to review this later" if random.choice([True, False]) else ""
            ) 