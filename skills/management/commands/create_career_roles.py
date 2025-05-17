from django.core.management.base import BaseCommand
from skills.models import CareerRole

class Command(BaseCommand):
    help = 'Creates default career roles in the database'

    def handle(self, *args, **options):
        career_roles = [
            ('Software Engineer', 'Development', 'Develops software applications using programming languages and frameworks'),
            ('Data Scientist', 'Data Science', 'Analyzes and interprets complex data to help make business decisions'),
            ('UX/UI Designer', 'Design', 'Creates user-friendly interfaces and experiences for websites and applications'),
            ('Product Manager', 'Management', 'Oversees the development and marketing of products'),
            ('DevOps Engineer', 'Operations', 'Manages the infrastructure and deployment of software'),
            ('Machine Learning Engineer', 'AI/ML', 'Builds machine learning models and implements them in applications'),
            ('Frontend Developer', 'Development', 'Specializes in building the user-facing parts of websites and applications'),
            ('Backend Developer', 'Development', 'Focuses on the server-side logic and databases of applications'),
            ('Full Stack Developer', 'Development', 'Works on both frontend and backend aspects of web applications'),
            ('Mobile App Developer', 'Development', 'Creates applications for mobile devices like smartphones and tablets'),
            ('Cloud Architect', 'Infrastructure', 'Designs and implements cloud computing solutions'),
            ('Cybersecurity Analyst', 'Security', 'Protects systems and networks from cyber threats'),
            ('Data Engineer', 'Data', 'Builds systems to collect, store, and analyze data'),
            ('Business Analyst', 'Business', 'Analyzes business needs and recommends solutions'),
            ('Technical Writer', 'Documentation', 'Creates clear documentation for technical products and processes')
        ]
        
        created_count = 0
        for name, category, description in career_roles:
            role, created = CareerRole.objects.get_or_create(
                name=name,
                defaults={
                    'category': category,
                    'description': description
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f"Created career role: {name}")
        
        self.stdout.write(self.style.SUCCESS(f"Successfully created {created_count} career roles")) 