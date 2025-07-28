from django.core.management.base import BaseCommand
from learning.models import Course, LearningResource, Achievement
from django.utils import timezone

class Command(BaseCommand):
    help = 'Populate the database with sample courses and learning resources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing courses before adding new ones',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing courses...')
            Course.objects.all().delete()
            LearningResource.objects.all().delete()
            Achievement.objects.all().delete()

        self.create_achievements()
        self.create_courses()
        self.create_learning_resources()

        self.stdout.write(
            self.style.SUCCESS('Successfully populated database with courses and learning resources!')
        )

    def create_achievements(self):
        """Create sample achievements"""
        achievements_data = [
            {
                'name': 'First Steps',
                'description': 'Complete your first course',
                'icon': '🎯',
                'requirement_type': 'courses_completed',
                'requirement_value': 1
            },
            {
                'name': 'Course Collector',
                'description': 'Complete 5 courses',
                'icon': '🏆',
                'requirement_type': 'courses_completed',
                'requirement_value': 5
            },
            {
                'name': 'Quiz Champion',
                'description': 'Score 90% or higher on 10 quizzes',
                'icon': '🧠',
                'requirement_type': 'quiz_excellence',
                'requirement_value': 10
            },
            {
                'name': 'Subject Explorer',
                'description': 'Create 5 different subjects',
                'icon': '📚',
                'requirement_type': 'subjects_created',
                'requirement_value': 5
            },
            {
                'name': 'Course Master',
                'description': 'Complete 10 courses',
                'icon': '🎓',
                'requirement_type': 'courses_completed',
                'requirement_value': 10
            },
            {
                'name': 'AI Assistant',
                'description': 'Have 20 chat sessions with the AI',
                'icon': '🤖',
                'requirement_type': 'chat_sessions',
                'requirement_value': 20
            },
            {
                'name': 'Material Curator',
                'description': 'Upload 15 learning materials',
                'icon': '📄',
                'requirement_type': 'materials_uploaded',
                'requirement_value': 15
            },
            {
                'name': 'Perfect Score',
                'description': 'Get 100% on any quiz',
                'icon': '💯',
                'requirement_type': 'perfect_quiz',
                'requirement_value': 1
            }
        ]

        for achievement_data in achievements_data:
            achievement, created = Achievement.objects.get_or_create(
                name=achievement_data['name'],
                defaults=achievement_data
            )
            if created:
                self.stdout.write(f'Created achievement: {achievement.name}')

    def create_courses(self):
        """Create sample courses"""
        courses_data = [
            {
                'title': 'Python Programming Fundamentals',
                'description': 'Learn the basics of Python programming from scratch. Cover variables, functions, loops, and object-oriented programming.',
                'instructor': 'Dr. Sarah Johnson',
                'duration_hours': 25,
                'difficulty_level': 'beginner'
            },
            {
                'title': 'Advanced JavaScript and ES6+',
                'description': 'Master modern JavaScript features including async/await, modules, classes, and advanced DOM manipulation.',
                'instructor': 'Mike Chen',
                'duration_hours': 30,
                'difficulty_level': 'intermediate'
            },
            {
                'title': 'Data Science with Python',
                'description': 'Comprehensive introduction to data science using Python, pandas, NumPy, and matplotlib for data analysis.',
                'instructor': 'Prof. Emily Davis',
                'duration_hours': 40,
                'difficulty_level': 'intermediate'
            },
            {
                'title': 'Machine Learning Basics',
                'description': 'Introduction to machine learning concepts, algorithms, and practical applications using scikit-learn.',
                'instructor': 'Dr. Alex Rodriguez',
                'duration_hours': 35,
                'difficulty_level': 'intermediate'
            },
            {
                'title': 'React.js Complete Guide',
                'description': 'Build modern web applications with React.js. Learn components, hooks, state management, and routing.',
                'instructor': 'Jessica Park',
                'duration_hours': 45,
                'difficulty_level': 'intermediate'
            },
            {
                'title': 'Database Design and SQL',
                'description': 'Learn database fundamentals, SQL queries, database design principles, and optimization techniques.',
                'instructor': 'Robert Wilson',
                'duration_hours': 28,
                'difficulty_level': 'beginner'
            },
            {
                'title': 'Cloud Computing with AWS',
                'description': 'Master AWS cloud services including EC2, S3, Lambda, and learn cloud architecture best practices.',
                'instructor': 'Maria Garcia',
                'duration_hours': 50,
                'difficulty_level': 'advanced'
            },
            {
                'title': 'Cybersecurity Fundamentals',
                'description': 'Learn essential cybersecurity concepts, threat analysis, encryption, and security best practices.',
                'instructor': 'David Kim',
                'duration_hours': 32,
                'difficulty_level': 'beginner'
            },
            {
                'title': 'UI/UX Design Principles',
                'description': 'Master user interface and user experience design principles, wireframing, and prototyping.',
                'instructor': 'Anna Thompson',
                'duration_hours': 30,
                'difficulty_level': 'beginner'
            },
            {
                'title': 'DevOps and CI/CD',
                'description': 'Learn DevOps practices, continuous integration, deployment pipelines, and infrastructure automation.',
                'instructor': 'Chris Martinez',
                'duration_hours': 38,
                'difficulty_level': 'advanced'
            },
            {
                'title': 'Mobile App Development with Flutter',
                'description': 'Build cross-platform mobile applications using Flutter and Dart programming language.',
                'instructor': 'Lisa Wang',
                'duration_hours': 42,
                'difficulty_level': 'intermediate'
            },
            {
                'title': 'Artificial Intelligence Foundations',
                'description': 'Introduction to AI concepts, neural networks, deep learning, and practical AI applications.',
                'instructor': 'Dr. James Lee',
                'duration_hours': 48,
                'difficulty_level': 'advanced'
            }
        ]

        for course_data in courses_data:
            course, created = Course.objects.get_or_create(
                title=course_data['title'],
                defaults=course_data
            )
            if created:
                self.stdout.write(f'Created course: {course.title}')

    def create_learning_resources(self):
        """Create sample learning resources"""
        resources_data = [
            {
                'title': 'Python Official Documentation',
                'resource_url': 'https://docs.python.org/',
                'platform': 'other',
                'level': 'beginner',
                'description': 'Official Python documentation with tutorials and reference materials.'
            },
            {
                'title': 'JavaScript MDN Web Docs',
                'resource_url': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript',
                'platform': 'other',
                'level': 'beginner',
                'description': 'Comprehensive JavaScript documentation and tutorials.'
            },
            {
                'title': 'React Official Tutorial',
                'resource_url': 'https://reactjs.org/tutorial/tutorial.html',
                'platform': 'other',
                'level': 'beginner',
                'description': 'Official React tutorial for building interactive applications.'
            },
            {
                'title': 'AWS Free Tier Guide',
                'resource_url': 'https://aws.amazon.com/free/',
                'platform': 'other',
                'level': 'beginner',
                'description': 'Get started with AWS cloud services using the free tier.'
            },
            {
                'title': 'SQL Tutorial on W3Schools',
                'resource_url': 'https://www.w3schools.com/sql/',
                'platform': 'other',
                'level': 'beginner',
                'description': 'Interactive SQL tutorial with examples and exercises.'
            },
            {
                'title': 'Machine Learning Course - Andrew Ng',
                'resource_url': 'https://www.coursera.org/learn/machine-learning',
                'platform': 'coursera',
                'level': 'intermediate',
                'description': 'Popular machine learning course by Stanford professor Andrew Ng.'
            },
            {
                'title': 'GitHub Git Handbook',
                'resource_url': 'https://guides.github.com/introduction/git-handbook/',
                'platform': 'other',
                'level': 'beginner',
                'description': 'Learn Git version control basics and best practices.'
            },
            {
                'title': 'CSS-Tricks Complete Guide to Flexbox',
                'resource_url': 'https://css-tricks.com/snippets/css/a-guide-to-flexbox/',
                'platform': 'other',
                'level': 'intermediate',
                'description': 'Comprehensive guide to CSS Flexbox layout.'
            }
        ]

        for resource_data in resources_data:
            resource, created = LearningResource.objects.get_or_create(
                title=resource_data['title'],
                defaults=resource_data
            )
            if created:
                self.stdout.write(f'Created learning resource: {resource.title}') 