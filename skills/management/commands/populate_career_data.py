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
            },
            {
                'name': 'Mobile App Developer',
                'description': 'Develops applications for mobile devices across different platforms and operating systems.',
                'category': 'Development'
            },
            {
                'name': 'Blockchain Developer',
                'description': 'Develops and implements blockchain technology and smart contracts.',
                'category': 'Development'
            },
            {
                'name': 'AI Research Engineer',
                'description': 'Conducts research in artificial intelligence and develops cutting-edge AI solutions.',
                'category': 'AI'
            },
            {
                'name': 'Site Reliability Engineer',
                'description': 'Ensures the reliability, scalability, and performance of large-scale systems.',
                'category': 'Operations'
            },
            {
                'name': 'Data Engineer',
                'description': 'Designs and builds systems for collecting, storing, and analyzing data at scale.',
                'category': 'Data Science'
            },
            {
                'name': 'Backend Developer',
                'description': 'Specializes in server-side logic, databases, and application architecture.',
                'category': 'Development'
            },
            {
                'name': 'Frontend Developer',
                'description': 'Creates responsive and interactive user interfaces using modern web technologies.',
                'category': 'Development'
            },
            {
                'name': 'Quality Assurance Engineer',
                'description': 'Ensures software quality through testing, automation, and best practices.',
                'category': 'Development'
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
                'essential': ['Python', 'Machine Learning', 'Deep Learning', 'Mathematics', 'Statistics'],
                'important': ['TensorFlow', 'PyTorch', 'Sklearn', 'Data Preprocessing', 'Model Deployment'],
                'nice_to_have': ['MLOps', 'Kubernetes', 'Cloud ML Platforms', 'Computer Vision', 'NLP']
            },
            'Cybersecurity Analyst': {
                'essential': ['Network Security', 'Security Tools', 'Risk Assessment', 'Incident Response', 'Security Protocols'],
                'important': ['Penetration Testing', 'Forensics', 'Security Frameworks', 'Cryptography', 'Security Automation'],
                'nice_to_have': ['Malware Analysis', 'Threat Intelligence', 'Cloud Security', 'Ethical Hacking', 'Security Architecture']
            },
            'Product Manager': {
                'essential': ['Product Strategy', 'User Research', 'Agile Methodologies', 'Data Analysis', 'Communication'],
                'important': ['Market Research', 'Project Management', 'Product Analytics', 'Stakeholder Management', 'Technical Understanding'],
                'nice_to_have': ['UX Design', 'Business Strategy', 'A/B Testing', 'Product Marketing', 'Industry Knowledge']
            },
            'Cloud Architect': {
                'essential': ['AWS', 'Azure', 'Cloud Architecture', 'Security', 'Networking'],
                'important': ['Kubernetes', 'Terraform', 'Microservices', 'DevOps', 'Cloud Security'],
                'nice_to_have': ['Multi-cloud', 'Serverless', 'Cost Optimization', 'Performance Tuning', 'Disaster Recovery']
            },
            'Mobile App Developer': {
                'essential': ['Swift/Kotlin', 'Mobile UI Design', 'RESTful APIs', 'Mobile SDKs', 'Version Control'],
                'important': ['React Native/Flutter', 'Mobile Security', 'App Performance', 'Local Storage', 'Push Notifications'],
                'nice_to_have': ['CI/CD for Mobile', 'App Store Guidelines', 'Cross-platform Development', 'Mobile Analytics', 'AR/VR']
            },
            'Blockchain Developer': {
                'essential': ['Solidity', 'Smart Contracts', 'Web3.js', 'Blockchain Protocols', 'Cryptography'],
                'important': ['Ethereum', 'DApp Development', 'Truffle/Hardhat', 'Security Best Practices', 'Gas Optimization'],
                'nice_to_have': ['Layer 2 Solutions', 'Cross-chain Development', 'DeFi Protocols', 'NFT Development', 'Blockchain Architecture']
            },
            'AI Research Engineer': {
                'essential': ['Deep Learning', 'Research Methods', 'Python', 'Mathematics', 'Scientific Writing'],
                'important': ['PyTorch/TensorFlow', 'Research Papers', 'Experimentation', 'Algorithm Design', 'Model Architecture'],
                'nice_to_have': ['Reinforcement Learning', 'GANs', 'Research Tools', 'High-Performance Computing', 'Ethics in AI']
            },
            'Site Reliability Engineer': {
                'essential': ['Linux Systems', 'Monitoring Tools', 'Automation', 'Incident Response', 'Performance Tuning'],
                'important': ['Infrastructure as Code', 'Cloud Platforms', 'Kubernetes', 'Observability', 'Load Balancing'],
                'nice_to_have': ['Chaos Engineering', 'Service Mesh', 'Distributed Systems', 'Security Practices', 'Database Management']
            },
            'Data Engineer': {
                'essential': ['SQL', 'Python', 'ETL Processes', 'Data Warehousing', 'Big Data Tools'],
                'important': ['Spark', 'Airflow', 'Data Modeling', 'Data Pipeline', 'Cloud Data Platforms'],
                'nice_to_have': ['Stream Processing', 'Data Governance', 'Machine Learning', 'Data Security', 'Data Quality']
            },
            'Backend Developer': {
                'essential': ['Python/Java/Node.js', 'Databases', 'API Design', 'Server Architecture', 'Authentication'],
                'important': ['Microservices', 'Message Queues', 'Caching', 'Testing', 'Security'],
                'nice_to_have': ['GraphQL', 'Docker', 'Cloud Services', 'Performance Optimization', 'Monitoring']
            },
            'Frontend Developer': {
                'essential': ['HTML', 'CSS', 'JavaScript', 'React/Vue/Angular', 'Responsive Design'],
                'important': ['TypeScript', 'State Management', 'Testing', 'Build Tools', 'Performance'],
                'nice_to_have': ['Web Assembly', 'Progressive Web Apps', 'Accessibility', 'Animation', 'Design Systems']
            },
            'Quality Assurance Engineer': {
                'essential': ['Test Planning', 'Automation Testing', 'Test Frameworks', 'Bug Tracking', 'Test Cases'],
                'important': ['Selenium', 'API Testing', 'Performance Testing', 'CI/CD', 'Test Management'],
                'nice_to_have': ['Security Testing', 'Mobile Testing', 'Load Testing', 'Test Strategy', 'Agile Testing']
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
        """Create sample courses."""
        courses_data = [
            # Full Stack Development Courses
            {
                'title': 'Complete Web Development Bootcamp',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/the-complete-web-development-bootcamp/',
                'description': 'Learn web development from scratch - HTML, CSS, JavaScript, Node.js, React, and more.',
                'difficulty': 'Beginner',
                'duration': '60 hours',
                'is_free': False,
                'skills': ['HTML', 'CSS', 'JavaScript', 'React', 'Node.js']
            },
            {
                'title': 'MERN Stack - MongoDB, Express, React, Node.js',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/mern-stack-front-to-back/',
                'description': 'Build full stack web applications with MongoDB, Express, React, and Node.js.',
                'difficulty': 'Intermediate',
                'duration': '45 hours',
                'is_free': False,
                'skills': ['MongoDB', 'Express.js', 'React', 'Node.js', 'Full Stack Development']
            },
            {
                'title': 'Django & React Full Stack Development',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/django-react-full-stack-development/',
                'description': 'Build full stack applications with Django and React.',
                'difficulty': 'Intermediate',
                'duration': '50 hours',
                'is_free': False,
                'skills': ['Python', 'Django', 'React', 'REST API', 'Full Stack Development']
            },

            # Data Science Courses
            {
                'title': 'Data Science Professional Certificate',
                'provider': 'IBM',
                'url': 'https://www.coursera.org/professional-certificates/ibm-data-science',
                'description': 'Master data science skills with Python, SQL, and machine learning.',
                'difficulty': 'Beginner',
                'duration': '12 months',
                'is_free': False,
                'skills': ['Python', 'SQL', 'Data Science', 'Machine Learning', 'Data Analysis']
            },
            {
                'title': 'Advanced Data Science with IBM',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/specializations/advanced-data-science-ibm',
                'description': 'Advanced data science techniques and machine learning applications.',
                'difficulty': 'Advanced',
                'duration': '6 months',
                'is_free': False,
                'skills': ['Machine Learning', 'Deep Learning', 'Big Data', 'Data Science', 'Python']
            },
            {
                'title': 'Data Science: Machine Learning',
                'provider': 'Harvard',
                'url': 'https://www.edx.org/course/data-science-machine-learning',
                'description': 'Build a movie recommendation system and learn the science behind one of the most popular and successful data science techniques.',
                'difficulty': 'Intermediate',
                'duration': '8 weeks',
                'is_free': False,
                'skills': ['Machine Learning', 'R', 'Data Science', 'Statistics', 'Data Analysis']
            },

            # DevOps Courses
            {
                'title': 'DevOps Engineering on AWS',
                'provider': 'A Cloud Guru',
                'url': 'https://acloudguru.com/course/aws-certified-devops-engineer-professional',
                'description': 'Learn DevOps practices and tools on AWS.',
                'difficulty': 'Advanced',
                'duration': '35 hours',
                'is_free': False,
                'skills': ['AWS', 'DevOps', 'CI/CD', 'Infrastructure as Code']
            },
            {
                'title': 'Docker and Kubernetes: The Complete Guide',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/docker-and-kubernetes-the-complete-guide/',
                'description': 'Build, test, and deploy Docker applications with Kubernetes while learning production-style development workflows.',
                'difficulty': 'Intermediate',
                'duration': '22 hours',
                'is_free': False,
                'skills': ['Docker', 'Kubernetes', 'DevOps', 'CI/CD', 'Containerization']
            },
            {
                'title': 'Terraform for AWS - Beginner to Advanced',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/terraform-beginner-to-advanced/',
                'description': 'Learn Terraform for AWS infrastructure automation.',
                'difficulty': 'Intermediate',
                'duration': '25 hours',
                'is_free': False,
                'skills': ['Terraform', 'AWS', 'Infrastructure as Code', 'DevOps']
            },

            # UX/UI Design Courses
            {
                'title': 'UI/UX Design Specialization',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/specializations/ui-ux-design',
                'description': 'Master modern UI/UX design principles and tools.',
                'difficulty': 'Beginner',
                'duration': '50 hours',
                'is_free': False,
                'skills': ['UI Design', 'UX Research', 'Figma', 'Prototyping']
            },
            {
                'title': 'Complete Web & Mobile Designer',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/complete-web-designer-mobile-designer-zero-to-mastery/',
                'description': 'Learn UI/UX design, Figma, and responsive web design.',
                'difficulty': 'Beginner',
                'duration': '40 hours',
                'is_free': False,
                'skills': ['UI Design', 'UX Design', 'Figma', 'Responsive Design', 'Web Design']
            },
            {
                'title': 'Advanced UI/UX Design',
                'provider': 'Interaction Design Foundation',
                'url': 'https://www.interaction-design.org/courses',
                'description': 'Advanced UI/UX design principles and methodologies.',
                'difficulty': 'Advanced',
                'duration': '60 hours',
                'is_free': False,
                'skills': ['UI Design', 'UX Research', 'Design Systems', 'User Testing', 'Prototyping']
            },

            # Machine Learning Courses
            {
                'title': 'Machine Learning Specialization',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/specializations/machine-learning-introduction',
                'description': 'Build machine learning models in Python using popular libraries.',
                'difficulty': 'Intermediate',
                'duration': '80 hours',
                'is_free': False,
                'skills': ['Python', 'Machine Learning', 'Deep Learning', 'TensorFlow', 'Data Science']
            },
            {
                'title': 'Deep Learning Specialization',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/specializations/deep-learning',
                'description': 'Master deep learning and break into AI.',
                'difficulty': 'Advanced',
                'duration': '5 months',
                'is_free': False,
                'skills': ['Deep Learning', 'Neural Networks', 'TensorFlow', 'Computer Vision', 'NLP']
            },
            {
                'title': 'Practical Deep Learning for Coders',
                'provider': 'fast.ai',
                'url': 'https://course.fast.ai/',
                'description': 'Practical deep learning course for coders.',
                'difficulty': 'Intermediate',
                'duration': '30 hours',
                'is_free': True,
                'skills': ['Deep Learning', 'PyTorch', 'Computer Vision', 'NLP', 'Machine Learning']
            },

            # Cybersecurity Courses
            {
                'title': 'Cybersecurity Specialization',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/specializations/cyber-security',
                'description': 'Comprehensive cybersecurity training from basics to advanced.',
                'difficulty': 'Intermediate',
                'duration': '70 hours',
                'is_free': False,
                'skills': ['Network Security', 'Security Tools', 'Risk Assessment', 'Incident Response']
            },
            {
                'title': 'Ethical Hacking Bootcamp',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/learn-ethical-hacking-from-scratch/',
                'description': 'Learn ethical hacking and penetration testing.',
                'difficulty': 'Intermediate',
                'duration': '45 hours',
                'is_free': False,
                'skills': ['Ethical Hacking', 'Penetration Testing', 'Network Security', 'Security Tools']
            },
            {
                'title': 'CompTIA Security+ Certification',
                'provider': 'CompTIA',
                'url': 'https://www.comptia.org/certifications/security',
                'description': 'Industry-recognized security certification.',
                'difficulty': 'Intermediate',
                'duration': '40 hours',
                'is_free': False,
                'skills': ['Network Security', 'Security Tools', 'Risk Management', 'Security Protocols']
            },

            # Product Management Courses
            {
                'title': 'Product Management Professional Certificate',
                'provider': 'Product School',
                'url': 'https://productschool.com/product-management-certification/',
                'description': 'Comprehensive product management training.',
                'difficulty': 'Intermediate',
                'duration': '40 hours',
                'is_free': False,
                'skills': ['Product Strategy', 'User Research', 'Agile Methodologies', 'Product Analytics']
            },
            {
                'title': 'Digital Product Management',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/specializations/product-management',
                'description': 'Modern product management for digital products.',
                'difficulty': 'Intermediate',
                'duration': '6 months',
                'is_free': False,
                'skills': ['Product Strategy', 'User Research', 'Data Analysis', 'Product Analytics']
            },
            {
                'title': 'Product Management A-Z',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/product-management-a-z/',
                'description': 'Complete product management course from basics to advanced.',
                'difficulty': 'Beginner',
                'duration': '35 hours',
                'is_free': False,
                'skills': ['Product Strategy', 'User Research', 'Agile', 'Product Analytics', 'Stakeholder Management']
            },

            # Cloud Architecture Courses
            {
                'title': 'AWS Certified Solutions Architect',
                'provider': 'A Cloud Guru',
                'url': 'https://acloudguru.com/course/aws-certified-solutions-architect-associate',
                'description': 'Prepare for the AWS Solutions Architect certification.',
                'difficulty': 'Advanced',
                'duration': '40 hours',
                'is_free': False,
                'skills': ['AWS', 'Cloud Architecture', 'Security', 'Networking']
            },
            {
                'title': 'Google Cloud Professional Cloud Architect',
                'provider': 'Google Cloud',
                'url': 'https://cloud.google.com/certification/cloud-architect',
                'description': 'Google Cloud architecture and design.',
                'difficulty': 'Advanced',
                'duration': '45 hours',
                'is_free': False,
                'skills': ['Google Cloud', 'Cloud Architecture', 'Security', 'Networking']
            },
            {
                'title': 'Azure Solutions Architect Expert',
                'provider': 'Microsoft',
                'url': 'https://www.microsoft.com/en-us/learning/certification-azure-solutions-architect.aspx',
                'description': 'Microsoft Azure architecture and design.',
                'difficulty': 'Advanced',
                'duration': '50 hours',
                'is_free': False,
                'skills': ['Azure', 'Cloud Architecture', 'Security', 'Networking']
            },

            # Mobile Development Courses
            {
                'title': 'iOS & Swift - The Complete iOS App Development Bootcamp',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/ios-13-app-development-bootcamp/',
                'description': 'Learn iOS app development with Swift from scratch.',
                'difficulty': 'Beginner',
                'duration': '55 hours',
                'is_free': False,
                'skills': ['Swift', 'iOS Development', 'Mobile UI Design', 'Mobile SDKs']
            },
            {
                'title': 'Android App Development with Kotlin',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/android-oreo-kotlin-app-masterclass/',
                'description': 'Build Android apps with Kotlin.',
                'difficulty': 'Intermediate',
                'duration': '45 hours',
                'is_free': False,
                'skills': ['Kotlin', 'Android Development', 'Mobile UI Design', 'Mobile SDKs']
            },
            {
                'title': 'React Native - The Practical Guide',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/react-native-the-practical-guide/',
                'description': 'Build cross-platform mobile apps with React Native.',
                'difficulty': 'Intermediate',
                'duration': '40 hours',
                'is_free': False,
                'skills': ['React Native', 'JavaScript', 'Mobile Development', 'Cross-platform Development']
            },

            # Blockchain Development Courses
            {
                'title': 'Blockchain Specialization',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/specializations/blockchain',
                'description': 'Learn blockchain technology and smart contract development.',
                'difficulty': 'Intermediate',
                'duration': '50 hours',
                'is_free': False,
                'skills': ['Blockchain', 'Smart Contracts', 'Solidity', 'Web3.js']
            },
            {
                'title': 'Ethereum and Solidity: The Complete Developer\'s Guide',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/ethereum-and-solidity-the-complete-developers-guide/',
                'description': 'Build smart contracts and DApps with Ethereum and Solidity.',
                'difficulty': 'Intermediate',
                'duration': '35 hours',
                'is_free': False,
                'skills': ['Ethereum', 'Solidity', 'Smart Contracts', 'Web3.js', 'DApp Development']
            },
            {
                'title': 'Blockchain A-Z™: Learn How To Build Your First Blockchain',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/build-your-blockchain-az/',
                'description': 'Build your own blockchain from scratch.',
                'difficulty': 'Intermediate',
                'duration': '30 hours',
                'is_free': False,
                'skills': ['Blockchain', 'Cryptography', 'Smart Contracts', 'Python']
            },

            # AI Research Courses
            {
                'title': 'Advanced AI: Deep Reinforcement Learning',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/learn/deep-reinforcement-learning',
                'description': 'Learn advanced AI concepts and research methods.',
                'difficulty': 'Advanced',
                'duration': '40 hours',
                'is_free': False,
                'skills': ['Deep Learning', 'Reinforcement Learning', 'Python', 'Research Methods']
            },
            {
                'title': 'Natural Language Processing Specialization',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/specializations/natural-language-processing',
                'description': 'Master NLP techniques and applications.',
                'difficulty': 'Advanced',
                'duration': '4 months',
                'is_free': False,
                'skills': ['NLP', 'Deep Learning', 'Python', 'Machine Learning']
            },
            {
                'title': 'Computer Vision Specialization',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/specializations/computer-vision',
                'description': 'Learn computer vision and image processing.',
                'difficulty': 'Advanced',
                'duration': '4 months',
                'is_free': False,
                'skills': ['Computer Vision', 'Deep Learning', 'Python', 'Image Processing']
            },

            # Site Reliability Engineering Courses
            {
                'title': 'Site Reliability Engineering: Measuring and Managing Reliability',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/learn/site-reliability-engineering-slos',
                'description': 'Learn SRE practices from Google engineers.',
                'difficulty': 'Advanced',
                'duration': '30 hours',
                'is_free': False,
                'skills': ['SRE', 'Monitoring', 'Automation', 'Performance Tuning']
            },
            {
                'title': 'Google SRE Professional Certificate',
                'provider': 'Google',
                'url': 'https://www.coursera.org/professional-certificates/google-sre',
                'description': 'Professional SRE certification from Google.',
                'difficulty': 'Advanced',
                'duration': '6 months',
                'is_free': False,
                'skills': ['SRE', 'Monitoring', 'Automation', 'Performance Tuning', 'Incident Response']
            },
            {
                'title': 'SRE Fundamentals',
                'provider': 'Linux Academy',
                'url': 'https://linuxacademy.com/course/sre-fundamentals/',
                'description': 'Learn the fundamentals of Site Reliability Engineering.',
                'difficulty': 'Intermediate',
                'duration': '25 hours',
                'is_free': False,
                'skills': ['SRE', 'Monitoring', 'Automation', 'Performance Tuning']
            },

            # Data Engineering Courses
            {
                'title': 'Data Engineering with Python',
                'provider': 'DataCamp',
                'url': 'https://www.datacamp.com/tracks/data-engineer-with-python',
                'description': 'Master the tools and techniques of data engineering.',
                'difficulty': 'Intermediate',
                'duration': '45 hours',
                'is_free': False,
                'skills': ['Python', 'SQL', 'ETL', 'Data Warehousing']
            },
            {
                'title': 'Big Data Engineering',
                'provider': 'Coursera',
                'url': 'https://www.coursera.org/specializations/big-data-engineering',
                'description': 'Learn big data engineering and processing.',
                'difficulty': 'Advanced',
                'duration': '6 months',
                'is_free': False,
                'skills': ['Big Data', 'Hadoop', 'Spark', 'Data Engineering', 'Python']
            },
            {
                'title': 'Apache Spark with Python',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/taming-big-data-with-apache-spark-hands-on/',
                'description': 'Learn big data processing with Apache Spark.',
                'difficulty': 'Intermediate',
                'duration': '35 hours',
                'is_free': False,
                'skills': ['Spark', 'Python', 'Big Data', 'Data Processing']
            },

            # Backend Development Courses
            {
                'title': 'Complete Node.js Developer',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/complete-nodejs-developer-zero-to-mastery/',
                'description': 'Build modern backend applications with Node.js.',
                'difficulty': 'Intermediate',
                'duration': '45 hours',
                'is_free': False,
                'skills': ['Node.js', 'Express.js', 'MongoDB', 'API Design']
            },
            {
                'title': 'Django for Beginners',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/django-python/',
                'description': 'Learn Django web framework for Python.',
                'difficulty': 'Beginner',
                'duration': '30 hours',
                'is_free': False,
                'skills': ['Python', 'Django', 'SQL', 'API Design']
            },
            {
                'title': 'Spring Boot Microservices',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/spring-boot-microservices-and-spring-cloud/',
                'description': 'Build microservices with Spring Boot.',
                'difficulty': 'Advanced',
                'duration': '40 hours',
                'is_free': False,
                'skills': ['Java', 'Spring Boot', 'Microservices', 'API Design']
            },

            # Frontend Development Courses
            {
                'title': 'React - The Complete Guide',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/react-the-complete-guide-incl-redux/',
                'description': 'Master React.js with Redux, Hooks, and more.',
                'difficulty': 'Intermediate',
                'duration': '48 hours',
                'is_free': False,
                'skills': ['React', 'JavaScript', 'Redux', 'Web Development']
            },
            {
                'title': 'Advanced CSS and Sass',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/advanced-css-and-sass/',
                'description': 'Master modern CSS and Sass.',
                'difficulty': 'Intermediate',
                'duration': '35 hours',
                'is_free': False,
                'skills': ['CSS', 'Sass', 'Responsive Design', 'CSS Animations']
            },
            {
                'title': 'TypeScript: The Complete Developer\'s Guide',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/typescript-the-complete-developers-guide/',
                'description': 'Master TypeScript for modern web development.',
                'difficulty': 'Intermediate',
                'duration': '30 hours',
                'is_free': False,
                'skills': ['TypeScript', 'JavaScript', 'Web Development', 'Object-Oriented Programming']
            },

            # Quality Assurance Courses
            {
                'title': 'Selenium WebDriver with Python',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/selenium-webdriver-with-python/',
                'description': 'Master automation testing with Selenium and Python.',
                'difficulty': 'Intermediate',
                'duration': '25 hours',
                'is_free': False,
                'skills': ['Selenium', 'Python', 'Automation Testing', 'Test Frameworks']
            },
            {
                'title': 'Complete Cypress.io Testing',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/cypress-io-testing/',
                'description': 'Learn modern web testing with Cypress.io.',
                'difficulty': 'Intermediate',
                'duration': '20 hours',
                'is_free': False,
                'skills': ['Cypress', 'JavaScript', 'Automation Testing', 'Web Testing']
            },
            {
                'title': 'API Testing with Postman',
                'provider': 'Udemy',
                'url': 'https://www.udemy.com/course/api-testing-with-postman/',
                'description': 'Master API testing with Postman.',
                'difficulty': 'Beginner',
                'duration': '15 hours',
                'is_free': False,
                'skills': ['API Testing', 'Postman', 'REST API', 'Test Automation']
            }
        ]
        
        courses_created = 0
        course_skills_created = 0
        
        for course_data in courses_data:
            skills = course_data.pop('skills')
            course, created = Course.objects.update_or_create(
                title=course_data['title'],
                defaults=course_data
            )
            
            if created:
                courses_created += 1
            
            # Add skills for the course
            for skill_name in skills:
                skill, _ = Skill.objects.get_or_create(name=skill_name)
                CourseSkill.objects.get_or_create(
                    course=course,
                    skill=skill,
                    defaults={'skill_name': skill_name}
                )
                course_skills_created += 1
        
        self.stdout.write(f'Created {courses_created} courses and {course_skills_created} course skills') 