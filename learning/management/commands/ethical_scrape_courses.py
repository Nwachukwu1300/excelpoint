# learning/management/commands/ethical_scrape_courses.py
from django.core.management.base import BaseCommand
from learning.services.ethical_course_scraper import EthicalCourseScraper
from skills.models import RoleSkill
import time

class Command(BaseCommand):
    help = 'Ethically scrape courses from multiple free sources for skills in the database'
    
    def add_arguments(self, parser):
        parser.add_argument('--skills', nargs='+', type=str, help='Specific skills to scrape courses for')
        parser.add_argument('--limit', type=int, default=3, help='Max courses per skill per source')
        
    def handle(self, *args, **options):
        scraper = EthicalCourseScraper()
        
        # Get skills to scrape
        if options['skills']:
            skills_to_scrape = options['skills']
        else:
            # Get all skills from role_skills
            skills_to_scrape = set(RoleSkill.objects.values_list('skill_name', flat=True).distinct())
            self.stdout.write(f"Found {len(skills_to_scrape)} skills in the database")
        
        # Scrape courses for each skill
        total_added = 0
        for skill in skills_to_scrape:
            self.stdout.write(f"Scraping courses for skill: {skill}")
            
            # Search for courses from all sources
            courses = scraper.scrape_all_sources(skill, max_per_source=options['limit'])
            
            # Save to database
            added = scraper.save_courses_to_db(courses, skill)
            total_added += added
            
            self.stdout.write(self.style.SUCCESS(
                f"Added {added} courses for '{skill}'"
            ))
            
            # Brief pause between skills
            time.sleep(1)
        
        self.stdout.write(self.style.SUCCESS(f"Total courses added: {total_added}"))