# skills/management/commands/populate_courses.py
from django.core.management.base import BaseCommand
from learning.services.course_scraper import CourseDataScraper
from skills.models import CareerRole, RoleSkill

class Command(BaseCommand):
    help = 'Populate course database with scraped courses for existing skills'
    
    def add_arguments(self, parser):
        parser.add_argument('--skills', nargs='+', type=str, help='Specific skills to scrape courses for')
        parser.add_argument('--roles', nargs='+', type=int, help='Role IDs to scrape courses for all their skills')
        parser.add_argument('--limit', type=int, default=5, help='Max courses per skill per platform')
        
    def handle(self, *args, **options):
        scraper = CourseDataScraper()
        skills_to_scrape = set()
        
        # Collect skills from specified roles
        if options['roles']:
            for role_id in options['roles']:
                try:
                    role_skills = RoleSkill.objects.filter(role_id=role_id)
                    for rs in role_skills:
                        skills_to_scrape.add(rs.skill_name)
                    self.stdout.write(f"Added {len(role_skills)} skills from role ID {role_id}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing role {role_id}: {e}"))
        
        # Add explicitly specified skills
        if options['skills']:
            for skill in options['skills']:
                skills_to_scrape.add(skill)
        
        # If no skills specified, get all skills from all roles
        if not skills_to_scrape:
            role_skills = RoleSkill.objects.all()
            for rs in role_skills:
                skills_to_scrape.add(rs.skill_name)
            self.stdout.write(f"Found {len(skills_to_scrape)} skills from all roles")
        
        # Scrape courses for each skill
        total_added = 0
        for skill in skills_to_scrape:
            self.stdout.write(f"Scraping courses for skill: {skill}")
            
            # Scrape from Udemy
            udemy_courses = scraper.scrape_udemy(skill, max_courses=options['limit'])
            udemy_added = scraper.save_courses_to_db(udemy_courses, skill)
            
            # Scrape from Coursera
            coursera_courses = scraper.scrape_coursera(skill, max_courses=options['limit'])
            coursera_added = scraper.save_courses_to_db(coursera_courses, skill)
            
            skill_total = udemy_added + coursera_added
            total_added += skill_total
            
            self.stdout.write(self.style.SUCCESS(
                f"Added {udemy_added} Udemy courses and {coursera_added} Coursera courses for '{skill}'"
            ))
        
        self.stdout.write(self.style.SUCCESS(f"Successfully added {total_added} new courses to the database"))