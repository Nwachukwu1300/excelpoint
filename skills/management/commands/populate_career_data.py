from django.core.management.base import BaseCommand
from django.db import transaction
from skills.models import CareerRole, RoleSkill, Course, CourseSkill, Skill

class Command(BaseCommand):
    help = 'Populates the database with sample career roles, skills, and courses'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate career data...')
        
        with transaction.atomic():
            # Create career roles
            self.create_career_roles()
            
            # Create role skills
            self.create_role_skills()
            
            # Create courses and course skills
            self.create_courses()
        
        self.stdout.write(self.style.SUCCESS('Successfully populated career data!'))
    
    def create_career_roles(self):
        """Create sample career roles."""
        roles_data = [
            {
                'name': 'Full Stack Developer',
                'description': 'Develops both client and server software, working with databases, APIs, and user interfaces.',
                'category': 'Development'
            },
            {
                'name': 'Data Scientist',
                'description': 'Analyzes and interprets complex data to help organizations make better decisions.',
                'category': 'Data Science'
            },
            {
                'name': 'DevOps Engineer',
                'description': 'Combines software development and IT operations, focusing on automation and infrastructure.',
                'category': 'Operations'
            },
            {
                'name': 'UX/UI Designer',
                'description': 'Creates user-friendly interfaces with a focus on enhancing user experience.',
                'category': 'Design'
            },
            {
                'name': 'Machine Learning Engineer',
                'description': 'Designs and implements machine learning models to solve complex problems.',
                'category': 'AI'
            },
            {
                'name': 'Cybersecurity Analyst',
                'description': 'Protects systems and networks from digital attacks and security breaches.',
                'category': 'Security'
            },
            {
                'name': 'Product Manager',
                'description': 'Oversees product development from conception to launch, balancing business needs with technical feasibility.',
                'category': 'Management'
            },
            {
                'name': 'Cloud Architect',
                'description': 'Designs and implements cloud infrastructure solutions for scalability and reliability.',
                'category': 'Cloud Computing'
            }
        ]
        
        # Create or update roles
        roles_created = 0
        for role_data in roles_data:
            role, created = CareerRole.objects.update_or_create(
                name=role_data['name'],
                defaults={
                    'description': role_data.get('description', ''),
                    'category': role_data.get('category', '')
                }
            )
            
            if created:
                roles_created += 1
        
        self.stdout.write(f'Created {roles_created} career roles')
    
    def create_role_skills(self):
        """Create skill requirements for each role."""
        role_skills_data = {
            'Full Stack Developer': {
                'essential': ['JavaScript', 'HTML', 'CSS', 'Python', 'SQL'],
                'important': ['React', 'Node.js', 'Git', 'Docker', 'API Design'],
                'nice_to_have': ['TypeScript', 'AWS', 'GraphQL', 'CI/CD', 'Microservices']
            },
            'Data Scientist': {
                'essential': ['Python', 'SQL', 'Statistics', 'Machine Learning', 'Data Visualization'],
                'important': ['R', 'Pandas', 'NumPy', 'Sklearn', 'Jupyter'],
                'nice_to_have': ['TensorFlow', 'PyTorch', 'Big Data', 'Cloud Computing', 'A/B Testing']
            },
            'DevOps Engineer': {
                'essential': ['Linux', 'Docker', 'Git', 'CI/CD', 'Cloud Platforms'],
                'important': ['Kubernetes', 'Terraform', 'Jenkins', 'Monitoring', 'Scripting'],
                'nice_to_have': ['AWS', 'Azure', 'Google Cloud', 'Security', 'Networking']
            },
            'UX/UI Designer': {
                'essential': ['UI Design', 'UX Research', 'Wireframing', 'Prototyping', 'User Testing'],
                'important': ['Figma', 'Adobe XD', 'User-Centered Design', 'Accessibility', 'Information Architecture'],
                'nice_to_have': ['HTML', 'CSS', 'JavaScript', 'Design Systems', 'Motion Design']
            },
            'Machine Learning Engineer': {
                'essential': ['Python', 'Machine Learning', 'Deep Learning', 'Statistics', 'Linear Algebra'],
                'important': ['TensorFlow', 'PyTorch', 'Scikit-learn', 'Data Preprocessing', 'Model Deployment'],
                'nice_to_have': ['Computer Vision', 'NLP', 'MLOps', 'Cloud ML Services', 'Reinforcement Learning']
            },
            'Cybersecurity Analyst': {
                'essential': ['Network Security', 'Security Tools', 'Risk Assessment', 'SIEM', 'Threat Intelligence'],
                'important': ['Penetration Testing', 'Incident Response', 'Security Frameworks', 'Encryption', 'Authentication'],
                'nice_to_have': ['Python', 'Cloud Security', 'Forensics', 'Malware Analysis', 'Security Architecture']
            },
            'Product Manager': {
                'essential': ['Product Strategy', 'Roadmapping', 'User Research', 'Stakeholder Management', 'Market Analysis'],
                'important': ['Agile', 'Data Analysis', 'Prioritization', 'Communication', 'Project Management'],
                'nice_to_have': ['UX Design', 'Technical Knowledge', 'A/B Testing', 'SQL', 'Business Metrics']
            },
            'Cloud Architect': {
                'essential': ['AWS/Azure/GCP', 'Infrastructure as Code', 'Networking', 'Security', 'Cloud Services'],
                'important': ['Kubernetes', 'Docker', 'Microservices', 'Serverless', 'Cost Optimization'],
                'nice_to_have': ['Multi-cloud', 'CI/CD', 'DevOps', 'Database Design', 'Performance Tuning']
            }
        }
        
        # Create role skills
        skills_created = 0
        for role_name, skills_by_importance in role_skills_data.items():
            try:
                role = CareerRole.objects.get(name=role_name)
                
                # Delete existing skills for this role
                RoleSkill.objects.filter(role=role).delete()
                
                # Create new skills
                for importance, skills in skills_by_importance.items():
                    for skill_name in skills:
                        RoleSkill.objects.create(
                            role=role,
                            skill_name=skill_name,
                            importance=importance
                        )
                        skills_created += 1
                        
            except CareerRole.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Role {role_name} not found'))
        
        self.stdout.write(f'Created {skills_created} role skills')
    
    def create_courses(self):
        """Create sample courses and map them to skills."""
        courses_data = [
            {
                'title': 'Modern JavaScript from the Beginning',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/modern-javascript-from-the-beginning/',
                'description': 'Learn modern JavaScript from the beginning - ES6, OOP, AJAX, Webpack',
                'difficulty': 'beginner',
                'duration': '20 hours',
                'is_free': False,
                'skills': [
                    {'name': 'JavaScript', 'level': 'intermediate'}
                ]
            },
            {
                'title': 'React - The Complete Guide',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/react-the-complete-guide-incl-redux/',
                'description': 'Dive in and learn React.js from scratch! Learn Reactjs, Hooks, Redux, React Routing, Animations, Next.js and more!',
                'difficulty': 'intermediate',
                'duration': '40 hours',
                'is_free': False,
                'skills': [
                    {'name': 'React', 'level': 'advanced'},
                    {'name': 'JavaScript', 'level': 'intermediate'}
                ]
            },
            {
                'title': 'Python for Data Science and Machine Learning Bootcamp',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/python-for-data-science-and-machine-learning-bootcamp/',
                'description': 'Learn how to use NumPy, Pandas, Seaborn, Matplotlib, Plotly, Scikit-Learn, Machine Learning, and more!',
                'difficulty': 'intermediate',
                'duration': '25 hours',
                'is_free': False,
                'skills': [
                    {'name': 'Python', 'level': 'intermediate'},
                    {'name': 'Machine Learning', 'level': 'basic'},
                    {'name': 'Data Visualization', 'level': 'intermediate'}
                ]
            },
            {
                'title': 'Complete Machine Learning & Data Science Bootcamp',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/complete-machine-learning-and-data-science-zero-to-mastery/',
                'description': 'Learn Data Science, Data Analysis, Machine Learning (Artificial Intelligence) and Python with Tensorflow, Pandas & more!',
                'difficulty': 'beginner',
                'duration': '42 hours',
                'is_free': False,
                'skills': [
                    {'name': 'Machine Learning', 'level': 'intermediate'},
                    {'name': 'Python', 'level': 'basic'},
                    {'name': 'TensorFlow', 'level': 'basic'}
                ]
            },
            {
                'title': 'Docker and Kubernetes: The Complete Guide',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/docker-and-kubernetes-the-complete-guide/',
                'description': 'Build, test, and deploy Docker applications with Kubernetes while learning production-style development workflows',
                'difficulty': 'advanced',
                'duration': '22 hours',
                'is_free': False,
                'skills': [
                    {'name': 'Docker', 'level': 'advanced'},
                    {'name': 'Kubernetes', 'level': 'intermediate'},
                    {'name': 'CI/CD', 'level': 'basic'}
                ]
            },
            {
                'title': 'Learn SQL Basics for Data Science',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/specializations/learn-sql-basics-data-science',
                'description': 'Apply SQL creatively to analyze and explore data; create data analysis datasets; perform feature engineering',
                'difficulty': 'beginner',
                'duration': '4 months',
                'is_free': True,
                'skills': [
                    {'name': 'SQL', 'level': 'intermediate'},
                    {'name': 'Data Analysis', 'level': 'basic'}
                ]
            },
            {
                'title': 'Google Cloud Platform Fundamentals',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/learn/gcp-fundamentals',
                'description': 'This course introduces you to important concepts and terminology for working with Google Cloud Platform (GCP).',
                'difficulty': 'beginner',
                'duration': '10 hours',
                'is_free': True,
                'skills': [
                    {'name': 'Google Cloud', 'level': 'basic'},
                    {'name': 'Cloud Platforms', 'level': 'basic'}
                ]
            },
            {
                'title': 'UI / UX Design Specialization',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/specializations/ui-ux-design',
                'description': 'Design High-Impact User Experiences. Research, design, and prototype effective, visually-driven websites and apps.',
                'difficulty': 'intermediate',
                'duration': '6 months',
                'is_free': True,
                'skills': [
                    {'name': 'UI Design', 'level': 'intermediate'},
                    {'name': 'UX Research', 'level': 'intermediate'},
                    {'name': 'Prototyping', 'level': 'intermediate'}
                ]
            },
            {
                'title': 'Deep Learning Specialization',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/specializations/deep-learning',
                'description': 'Become a Deep Learning Expert. Master Deep Learning and Break into AI',
                'difficulty': 'advanced',
                'duration': '3 months',
                'is_free': True,
                'skills': [
                    {'name': 'Deep Learning', 'level': 'advanced'},
                    {'name': 'TensorFlow', 'level': 'intermediate'},
                    {'name': 'PyTorch', 'level': 'basic'}
                ]
            },
            {
                'title': 'Introduction to Cybersecurity',
                'provider': 'edX',
                'url': 'https://www.edx.org/course/introduction-to-cybersecurity',
                'description': 'Learn the fundamental principles of computer security and risk management.',
                'difficulty': 'beginner',
                'duration': '8 weeks',
                'is_free': True,
                'skills': [
                    {'name': 'Network Security', 'level': 'basic'},
                    {'name': 'Risk Assessment', 'level': 'basic'}
                ]
            },
            {
                'title': 'Agile with Atlassian Jira',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/learn/agile-atlassian-jira',
                'description': 'Plan, track, and release great products with Jira Software',
                'difficulty': 'beginner',
                'duration': '15 hours',
                'is_free': True,
                'skills': [
                    {'name': 'Agile', 'level': 'intermediate'},
                    {'name': 'Project Management', 'level': 'basic'}
                ]
            },
            {
                'title': 'AWS Cloud Technical Essentials',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/learn/aws-cloud-technical-essentials',
                'description': 'Learn the foundations of cloud computing and how AWS can help your business.',
                'difficulty': 'beginner',
                'duration': '16 hours',
                'is_free': True,
                'skills': [
                    {'name': 'AWS', 'level': 'basic'},
                    {'name': 'Cloud Platforms', 'level': 'basic'}
                ]
            }
        ]
        
        # Create courses and course skills
        courses_created = 0
        course_skills_created = 0
        
        for course_data in courses_data:
            # Extract skills
            skills_data = course_data.pop('skills', [])
            
            # Create course
            course, created = Course.objects.update_or_create(
                title=course_data['title'],
                provider=course_data['provider'],
                defaults=course_data
            )
            
            if created:
                courses_created += 1
            
            # Add skills to course (direct many-to-many)
            course.skills_taught.clear()
            
            for skill_data in skills_data:
                skill_name = skill_data['name']
                
                # Find or create the skill
                skill, _ = Skill.objects.get_or_create(
                    name=skill_name,
                    defaults={
                        'category': 'technical',  # Default category
                        'description': f"Skill taught in course: {course.title}"
                    }
                )
                
                # Add skill to course
                course.skills_taught.add(skill)
                course_skills_created += 1
                
                # Also create a CourseSkill for additional metadata
                CourseSkill.objects.update_or_create(
                    course=course,
                    skill_name=skill_name,
                    defaults={
                        'skill': skill,
                        'proficiency_level': skill_data.get('level', 'intermediate')
                    }
                )
        
        self.stdout.write(f'Created {courses_created} courses and {course_skills_created} course skills') 