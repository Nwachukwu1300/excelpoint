# learning/services/course_scraper.py
import requests
from bs4 import BeautifulSoup
import json
import time
import random
from django.core.management.base import BaseCommand
from skills.models import Course, CourseSkill

class CourseDataScraper:
    """Scrapes course data from learning platforms."""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def scrape_udemy(self, keyword, max_courses=5):
        """Scrape courses from Udemy search results."""
        base_url = f"https://www.udemy.com/courses/search/?q={keyword}&sort=relevance"
        courses = []
        
        try:
            response = requests.get(base_url, headers=self.headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract course information
                course_cards = soup.select('.course-card')[:max_courses]
                
                for card in course_cards:
                    try:
                        title_elem = card.select_one('.course-card--course-title')
                        link_elem = card.select_one('a.course-card--link')
                        instructor = card.select_one('.course-card--instructor-text')
                        price = card.select_one('.price-text__current')
                        
                        if title_elem and link_elem:
                            title = title_elem.text.strip()
                            url = 'https://www.udemy.com' + link_elem['href']
                            
                            course_data = {
                                'title': title,
                                'provider': 'Udemy',
                                'url': url,
                                'instructor': instructor.text.strip() if instructor else "",
                                'price': price.text.strip() if price else "Free",
                                'is_free': price.text.strip() == "Free" if price else True,
                                'description': f"Udemy course about {keyword}",
                                'difficulty': self._estimate_difficulty(title),
                                'duration': "Self-paced",
                                'skill_name': keyword
                            }
                            courses.append(course_data)
                    except Exception as e:
                        print(f"Error parsing course card: {e}")
            
            return courses
        except Exception as e:
            print(f"Error scraping Udemy courses: {e}")
            return []
    
    def scrape_coursera(self, keyword, max_courses=5):
        """Scrape courses from Coursera search results."""
        base_url = f"https://www.coursera.org/search?query={keyword}"
        courses = []
        
        try:
            response = requests.get(base_url, headers=self.headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract course information
                course_cards = soup.select('.cds-9.css-0.cds-10.cds-grid-item.cds-56')[:max_courses]
                
                for card in course_cards:
                    try:
                        title_elem = card.select_one('h2.cds-33.css-1sktkll.cds-35')
                        link_elem = card.select_one('a')
                        provider = card.select_one('div.cds-33.css-1cnqw7o.cds-35')
                        
                        if title_elem and link_elem:
                            title = title_elem.text.strip()
                            url = 'https://www.coursera.org' + link_elem['href']
                            
                            course_data = {
                                'title': title,
                                'provider': 'Coursera',
                                'url': url,
                                'institution': provider.text.strip() if provider else "Coursera Partner",
                                'is_free': False,  # Most Coursera courses aren't entirely free
                                'description': f"Coursera course about {keyword}",
                                'difficulty': self._estimate_difficulty(title),
                                'duration': "4-6 weeks",
                                'skill_name': keyword
                            }
                            courses.append(course_data)
                    except Exception as e:
                        print(f"Error parsing Coursera course card: {e}")
            
            return courses
        except Exception as e:
            print(f"Error scraping Coursera courses: {e}")
            return []
    
    def _estimate_difficulty(self, title):
        """Estimate course difficulty based on title."""
        title_lower = title.lower()
        if any(word in title_lower for word in ['beginner', 'basics', 'introduction', 'getting started']):
            return 'beginner'
        elif any(word in title_lower for word in ['advanced', 'expert', 'mastery']):
            return 'advanced'
        else:
            return 'intermediate'
    
    def save_courses_to_db(self, courses, skill_name):
        """Save scraped courses to database."""
        count = 0
        for course_data in courses:
            try:
                # Create or update course
                course, created = Course.objects.update_or_create(
                    title=course_data['title'],
                    provider=course_data['provider'],
                    defaults={
                        'url': course_data['url'],
                        'description': course_data['description'],
                        'difficulty': course_data['difficulty'],
                        'duration': course_data['duration'],
                        'is_free': course_data.get('is_free', False)
                    }
                )
                
                # Create course-skill relationship
                CourseSkill.objects.update_or_create(
                    course=course,
                    skill_name=skill_name,
                    defaults={
                        'proficiency_level': 'intermediate'
                    }
                )
                
                if created:
                    count += 1
            except Exception as e:
                print(f"Error saving course {course_data['title']}: {e}")
        
        return count