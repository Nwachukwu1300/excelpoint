import os
import django
import random

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from skills.models import Course, CourseSkill, Skill

# List of common tech skills
TECH_SKILLS = [
    'Python', 'JavaScript', 'React', 'Django', 'Node.js', 'HTML', 'CSS',
    'Data Science', 'Machine Learning', 'SQL', 'AWS', 'Docker', 'Git',
    'DevOps', 'Cybersecurity', 'UI/UX Design', 'Product Management',
    'Agile Methodology', 'Swift', 'Kotlin', 'Java', 'C#', 'C++',
    'Ruby', 'Go', 'PHP', 'TypeScript', 'TensorFlow', 'PyTorch'
]

# Sample course data
SAMPLE_COURSES = [
    {
        'title': 'Python for Beginners: Learn Programming Basics',
        'provider': 'Udemy',
        'url': 'https://www.udemy.com/course/python-for-beginners/',
        'description': 'A comprehensive introduction to Python programming language with hands-on projects.',
        'difficulty': 'beginner',
        'duration': '12 hours',
        'is_free': False,
        'skills': ['Python', 'Programming Fundamentals']
    },
    {
        'title': 'The Complete JavaScript Course',
        'provider': 'Udemy',
        'url': 'https://www.udemy.com/course/the-complete-javascript-course/',
        'description': 'Master JavaScript with projects, challenges and theory. Suitable for beginners and experienced developers.',
        'difficulty': 'intermediate',
        'duration': '69 hours',
        'is_free': False,
        'skills': ['JavaScript', 'Web Development', 'HTML', 'CSS']
    },
    {
        'title': 'React - The Complete Guide',
        'provider': 'Udemy',
        'url': 'https://www.udemy.com/course/react-the-complete-guide-incl-redux/',
        'description': 'Dive in and learn React.js from scratch! Learn React, Hooks, Redux, React Router, Next.js, and more!',
        'difficulty': 'intermediate',
        'duration': '49 hours',
        'is_free': False,
        'skills': ['React', 'JavaScript', 'Redux', 'Web Development']
    },
    {
        'title': 'Django for Beginners',
        'provider': 'Coursera',
        'url': 'https://www.coursera.org/learn/django-for-beginners',
        'description': 'Learn how to build web applications with Django, the popular Python web framework.',
        'difficulty': 'beginner',
        'duration': '20 hours',
        'is_free': True,
        'skills': ['Django', 'Python', 'Web Development']
    },
    {
        'title': 'Machine Learning A-Z™: Hands-On Python & R',
        'provider': 'Udemy',
        'url': 'https://www.udemy.com/course/machinelearning/',
        'description': 'Learn to create Machine Learning Algorithms in Python and R from two Data Science experts.',
        'difficulty': 'intermediate',
        'duration': '44 hours',
        'is_free': False,
        'skills': ['Machine Learning', 'Python', 'Data Science', 'R']
    },
    {
        'title': 'AWS Certified Solutions Architect - Associate',
        'provider': 'edX',
        'url': 'https://www.edx.org/learn/aws/amazon-web-services-aws-certified-solutions-architect-associate',
        'description': 'Prepare for the AWS Certified Solutions Architect - Associate certification exam.',
        'difficulty': 'advanced',
        'duration': '30 hours',
        'is_free': False,
        'skills': ['AWS', 'Cloud Computing', 'Solutions Architecture']
    },
    {
        'title': 'Data Science Specialization',
        'provider': 'Coursera',
        'url': 'https://www.coursera.org/specializations/jhu-data-science',
        'description': 'Launch your career in data science. A ten-course introduction to data science, developed and taught by leading professors.',
        'difficulty': 'intermediate',
        'duration': '80 hours',
        'is_free': True,
        'skills': ['Data Science', 'R', 'Statistics', 'Machine Learning']
    },
    {
        'title': 'The Complete Web Developer Course',
        'provider': 'Udemy',
        'url': 'https://www.udemy.com/course/the-complete-web-developer-course-2/',
        'description': 'Learn Web Development by building 25 websites and mobile apps using HTML, CSS, Javascript, PHP, Python, MySQL & more!',
        'difficulty': 'beginner',
        'duration': '30 hours',
        'is_free': False,
        'skills': ['HTML', 'CSS', 'JavaScript', 'PHP', 'Python', 'MySQL']
    },
    {
        'title': 'Deep Learning Specialization',
        'provider': 'Coursera',
        'url': 'https://www.coursera.org/specializations/deep-learning',
        'description': 'The Deep Learning Specialization is a foundational program that will help you understand the capabilities, challenges, and consequences of deep learning.',
        'difficulty': 'advanced',
        'duration': '100 hours',
        'is_free': True,
        'skills': ['Deep Learning', 'TensorFlow', 'Neural Networks', 'Python']
    },
    {
        'title': 'Git & GitHub Crash Course',
        'provider': 'Udemy',
        'url': 'https://www.udemy.com/course/git-and-github-crash-course/',
        'description': 'Master the essentials and the tricky bits: rebasing, squashing, stashing, branching, pull requests and more.',
        'difficulty': 'beginner',
        'duration': '4 hours',
        'is_free': True,
        'skills': ['Git', 'GitHub', 'Version Control']
    },
    {
        'title': 'UI/UX Design Specialization',
        'provider': 'Coursera',
        'url': 'https://www.coursera.org/specializations/ui-ux-design',
        'description': 'Design High-Impact User Experiences. Research, design, and prototype effective, visually-driven websites and apps.',
        'difficulty': 'intermediate',
        'duration': '50 hours',
        'is_free': True,
        'skills': ['UI Design', 'UX Design', 'User Research', 'Prototyping']
    },
    {
        'title': 'The Complete Node.js Developer Course',
        'provider': 'Udemy',
        'url': 'https://www.udemy.com/course/the-complete-nodejs-developer-course-2/',
        'description': 'Learn Node.js by building real-world applications with Node, Express, MongoDB, Jest, and more!',
        'difficulty': 'intermediate',
        'duration': '35 hours',
        'is_free': False,
        'skills': ['Node.js', 'Express.js', 'MongoDB', 'JavaScript']
    }
]

def create_sample_courses():
    # Delete any existing courses (optional)
    # Course.objects.all().delete()
    
    # Create or get skills
    all_skills = {}
    for course_data in SAMPLE_COURSES:
        for skill_name in course_data['skills']:
            if skill_name not in all_skills:
                skill, created = Skill.objects.get_or_create(name=skill_name)
                all_skills[skill_name] = skill
    
    # Create courses and associate skills
    courses_created = 0
    for course_data in SAMPLE_COURSES:
        # Extract skills from course data
        skills = course_data.pop('skills')
        
        # Create the course
        course, created = Course.objects.get_or_create(
            title=course_data['title'],
            defaults=course_data
        )
        
        if created:
            courses_created += 1
            
            # Associate skills with the course
            for skill_name in skills:
                skill = all_skills[skill_name]
                course.skills_taught.add(skill)
                
                # Create CourseSkill relationship
                CourseSkill.objects.get_or_create(
                    course=course,
                    skill=skill,
                    skill_name=skill_name,
                    proficiency_level=random.choice(['basic', 'intermediate', 'advanced'])
                )
    
    return courses_created

if __name__ == '__main__':
    courses_created = create_sample_courses()
    print(f"Successfully created {courses_created} sample courses!") 