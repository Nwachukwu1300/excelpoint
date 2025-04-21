# learning/services/ethical_course_scraper.py
import requests
from bs4 import BeautifulSoup
import time
import random
import json
import os
import re
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from datetime import datetime, timedelta
from django.conf import settings
from skills.models import Course, CourseSkill

class EthicalCourseScraper:
    """
    Ethically scrapes course data from learning platforms with proper rate limiting,
    respect for robots.txt, and clear identification.
    """
    
    def __init__(self):
        self.user_agent = "CareerNexusCourseBot/1.0 (+https://your-domain.com/bot-info) Educational Project"
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
        }
        
        # Cache directory setup
        self.cache_dir = os.path.join(settings.BASE_DIR, 'cache', 'course_data')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Rate limiting settings (requests per minute for each domain)
        self.rate_limits = {
            'www.coursera.org': 10,
            'www.edx.org': 10,
            'www.futurelearn.com': 5,
            'www.codecademy.com': 8,
            'www.khanacademy.org': 10,
            'www.freecodecamp.org': 15,
            'www.w3schools.com': 10,
            'developer.mozilla.org': 15
        }
        
        # Track last request time for each domain
        self.last_request_time = {}
        
        # Robots.txt parser cache
        self.robots_parsers = {}
    
    def _get_robots_parser(self, domain):
        """Get or create a robots.txt parser for a domain."""
        if domain not in self.robots_parsers:
            parser = RobotFileParser()
            parser.set_url(f"https://{domain}/robots.txt")
            try:
                parser.read()
                self.robots_parsers[domain] = parser
            except Exception as e:
                print(f"Error reading robots.txt for {domain}: {e}")
                # Default to a conservative approach if robots.txt can't be read
                self.robots_parsers[domain] = None
        
        return self.robots_parsers[domain]
    
    def _can_fetch(self, url):
        """Check if scraping is allowed for this URL according to robots.txt."""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path
        
        robots = self._get_robots_parser(domain)
        if robots is None:
            # If we couldn't parse robots.txt, be conservative
            return False
            
        return robots.can_fetch(self.user_agent, url)
    
    def _respect_rate_limit(self, domain):
        """Implement rate limiting for each domain."""
        # Default rate limit: 10 requests per minute
        requests_per_minute = self.rate_limits.get(domain, 10)
        min_interval = 60.0 / requests_per_minute
        
        current_time = time.time()
        if domain in self.last_request_time:
            elapsed = current_time - self.last_request_time[domain]
            if elapsed < min_interval:
                # Wait until we can make another request
                sleep_time = min_interval - elapsed
                print(f"Rate limiting: waiting {sleep_time:.2f}s for {domain}")
                time.sleep(sleep_time)
        
        # Update last request time
        self.last_request_time[domain] = time.time()
    
    def _get_cache_key(self, url, params=None):
        """Generate a cache key for a URL and optional parameters."""
        if params:
            param_str = json.dumps(params, sort_keys=True)
            return f"{url}_{hash(param_str)}"
        return url
    
    def _get_cached_data(self, cache_key):
        """Get data from cache if it exists and is fresh."""
        cache_file = os.path.join(self.cache_dir, f"{hash(cache_key)}.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                    
                # Check if cache is still valid (less than 24 hours old)
                cache_time = datetime.fromtimestamp(cached_data.get('timestamp', 0))
                if datetime.now() - cache_time < timedelta(hours=24):
                    return cached_data.get('data')
            except Exception as e:
                print(f"Error reading cache: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key, data):
        """Save data to cache with timestamp."""
        cache_file = os.path.join(self.cache_dir, f"{hash(cache_key)}.json")
        
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().timestamp(),
                    'data': data
                }, f)
        except Exception as e:
            print(f"Error writing to cache: {e}")
    
    def _fetch_with_retries(self, url, params=None, max_retries=3):
        """Fetch a URL with retries and rate limiting."""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Check if we're allowed to scrape this URL
        if not self._can_fetch(url):
            print(f"Robots.txt disallows scraping: {url}")
            return None
        
        # Check cache first
        cache_key = self._get_cache_key(url, params)
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            print(f"Using cached data for: {url}")
            return cached_data
        
        # Apply rate limiting
        self._respect_rate_limit(domain)
        
        # Make the request with retries
        retry_count = 0
        while retry_count < max_retries:
            try:
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    params=params,
                    timeout=15  # 15 second timeout
                )
                
                if response.status_code == 200:
                    # Save to cache and return
                    self._save_to_cache(cache_key, response.text)
                    return response.text
                elif response.status_code == 429:  # Too Many Requests
                    # Exponential backoff
                    wait_time = 2 ** retry_count + random.random()
                    print(f"Rate limited (429). Waiting {wait_time:.2f}s before retry")
                    time.sleep(wait_time)
                else:
                    print(f"Request failed with status code: {response.status_code}")
                    return None
            except requests.exceptions.RequestException as e:
                print(f"Request error: {e}")
                wait_time = 2 ** retry_count + random.random()
                print(f"Waiting {wait_time:.2f}s before retry")
                time.sleep(wait_time)
            
            retry_count += 1
        
        print(f"Failed to fetch {url} after {max_retries} retries")
        return None
    
    def scrape_freecodecamp(self, skill, max_courses=5):
        """Scrape courses from freeCodeCamp that match the skill."""
        base_url = "https://www.freecodecamp.org/news"
        search_url = f"{base_url}/search?query={skill}"
        
        courses = []
        html = self._fetch_with_retries(search_url)
        if not html:
            return courses
            
        soup = BeautifulSoup(html, 'html.parser')
        articles = soup.select('article.post-card')[:max_courses]
        
        for article in articles:
            try:
                title_elem = article.select_one('h2.post-card-title')
                link_elem = article.select_one('a.post-card-image-link')
                excerpt_elem = article.select_one('section.post-card-excerpt p')
                
                if title_elem and link_elem:
                    title = title_elem.text.strip()
                    url = f"https://www.freecodecamp.org{link_elem['href']}"
                    description = excerpt_elem.text.strip() if excerpt_elem else ""
                    
                    # Only include if it's likely a tutorial or course
                    if self._is_likely_course(title, description):
                        course_data = {
                            'title': title,
                            'provider': 'freeCodeCamp',
                            'url': url,
                            'description': description,
                            'difficulty': self._estimate_difficulty(title, description),
                            'duration': 'Self-paced',
                            'is_free': True,
                            'skill_name': skill
                        }
                        courses.append(course_data)
            except Exception as e:
                print(f"Error parsing freeCodeCamp article: {e}")
        
        return courses
    
    def scrape_codecademy(self, skill, max_courses=5):
        """Scrape courses from Codecademy that match the skill."""
        search_url = f"https://www.codecademy.com/search?query={skill}"
        
        courses = []
        html = self._fetch_with_retries(search_url)
        if not html:
            return courses
            
        soup = BeautifulSoup(html, 'html.parser')
        course_cards = soup.select('.gamut-1y88wvm-Box.euuosba0')[:max_courses]
        
        for card in course_cards:
            try:
                title_elem = card.select_one('h3')
                link_elem = card.select_one('a[href*="/courses/"]')
                desc_elem = card.select_one('p')
                
                if title_elem and link_elem:
                    title = title_elem.text.strip()
                    url = f"https://www.codecademy.com{link_elem['href']}"
                    description = desc_elem.text.strip() if desc_elem else ""
                    
                    course_data = {
                        'title': title,
                        'provider': 'Codecademy',
                        'url': url,
                        'description': description,
                        'difficulty': self._estimate_difficulty(title, description),
                        'duration': 'Self-paced',
                        'is_free': False,  # Codecademy requires Pro for most courses
                        'skill_name': skill
                    }
                    courses.append(course_data)
            except Exception as e:
                print(f"Error parsing Codecademy course: {e}")
        
        return courses
    
    def scrape_khanacademy(self, skill, max_courses=5):
        """Scrape courses from Khan Academy that match the skill."""
        search_url = f"https://www.khanacademy.org/search?page_search_query={skill}"
        
        courses = []
        html = self._fetch_with_retries(search_url)
        if not html:
            return courses
            
        soup = BeautifulSoup(html, 'html.parser')
        results = soup.select('.search-result')[:max_courses]
        
        for result in results:
            try:
                title_elem = result.select_one('.search-result-title')
                link_elem = result.select_one('a')
                desc_elem = result.select_one('.search-result-description')
                
                if title_elem and link_elem:
                    title = title_elem.text.strip()
                    url = f"https://www.khanacademy.org{link_elem['href']}"
                    description = desc_elem.text.strip() if desc_elem else ""
                    
                    course_data = {
                        'title': title,
                        'provider': 'Khan Academy',
                        'url': url,
                        'description': description,
                        'difficulty': self._estimate_difficulty(title, description),
                        'duration': 'Self-paced',
                        'is_free': True,
                        'skill_name': skill
                    }
                    courses.append(course_data)
            except Exception as e:
                print(f"Error parsing Khan Academy course: {e}")
        
        return courses
    
    def scrape_w3schools(self, skill, max_courses=5):
        """Scrape tutorials from W3Schools that match the skill."""
        base_url = "https://www.w3schools.com"
        
        # W3Schools doesn't have a search API, so we'll use a mapping of skills to tutorials
        skill_map = {
            'python': '/python/default.asp',
            'javascript': '/js/default.asp',
            'html': '/html/default.asp',
            'css': '/css/default.asp',
            'sql': '/sql/default.asp',
            'php': '/php/default.asp',
            'java': '/java/default.asp',
            'c++': '/cpp/default.asp',
            'c#': '/cs/default.asp',
            'react': '/react/default.asp',
            'node.js': '/nodejs/default.asp',
            'jquery': '/jquery/default.asp',
            'bootstrap': '/bootstrap/bootstrap_ver.asp',
            'r': '/r/default.asp',
            'kotlin': '/kotlin/index.php',
            'go': '/go/index.php',
            'mongodb': '/mongodb/index.php',
            'aws': '/aws/index.php',
            'xml': '/xml/default.asp',
            'django': '/django/index.php'
        }
        
        # Find the best match for the skill
        skill_lower = skill.lower()
        path = None
        
        # Exact match
        if skill_lower in skill_map:
            path = skill_map[skill_lower]
        else:
            # Partial match
            for k, v in skill_map.items():
                if k in skill_lower or skill_lower in k:
                    path = v
                    break
        
        if not path:
            return []  # No matching tutorial
            
        url = base_url + path
        courses = []
        
        html = self._fetch_with_retries(url)
        if not html:
            return courses
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title and description
        title_elem = soup.select_one('h1') or soup.select_one('h2')
        title = title_elem.text.strip() if title_elem else f"{skill.capitalize()} Tutorial"
        
        desc_elem = soup.select_one('div.intro') or soup.select_one('div.w3-panel')
        description = desc_elem.text.strip() if desc_elem else f"Learn {skill} with W3Schools tutorials"
        
        course_data = {
            'title': title,
            'provider': 'W3Schools',
            'url': url,
            'description': description,
            'difficulty': 'beginner',
            'duration': 'Self-paced',
            'is_free': True,
            'skill_name': skill
        }
        courses.append(course_data)
        
        return courses
    
    def scrape_mdn(self, skill, max_courses=5):
        """Scrape tutorials from MDN Web Docs that match the skill."""
        search_url = f"https://developer.mozilla.org/en-US/search?q={skill}"
        
        courses = []
        html = self._fetch_with_retries(search_url)
        if not html:
            return courses
            
        soup = BeautifulSoup(html, 'html.parser')
        results = soup.select('.search-result-entry')[:max_courses]
        
        for result in results:
            try:
                title_elem = result.select_one('.search-result-heading')
                link_elem = result.select_one('a')
                excerpt_elem = result.select_one('.search-result-excerpt')
                
                if title_elem and link_elem:
                    title = title_elem.text.strip()
                    url = f"https://developer.mozilla.org{link_elem['href']}"
                    description = excerpt_elem.text.strip() if excerpt_elem else ""
                    
                    # Only include if it looks like a guide/tutorial
                    if any(word in title.lower() for word in ['guide', 'tutorial', 'introduction', 'learn']):
                        course_data = {
                            'title': title,
                            'provider': 'MDN Web Docs',
                            'url': url,
                            'description': description,
                            'difficulty': self._estimate_difficulty(title, description),
                            'duration': 'Self-paced',
                            'is_free': True,
                            'skill_name': skill
                        }
                        courses.append(course_data)
            except Exception as e:
                print(f"Error parsing MDN tutorial: {e}")
        
        return courses
    
    def _is_likely_course(self, title, description):
        """Check if the content is likely to be a course or tutorial."""
        keywords = [
            'tutorial', 'course', 'learn', 'guide', 'introduction', 
            'beginner', 'advanced', 'mastering', 'complete', 'programming',
            'development', 'training', 'lesson', 'class', 'workshop'
        ]
        
        text = (title + " " + description).lower()
        return any(keyword in text for keyword in keywords)
    
    def _estimate_difficulty(self, title, description):
        """Estimate course difficulty based on title and description."""
        text = (title + " " + description).lower()
        
        # Check for beginner indicators
        beginner_terms = [
            'beginner', 'basic', 'start', 'introduction', 'intro',
            'fundamental', 'getting started', 'basics', 'novice'
        ]
        
        # Check for advanced indicators
        advanced_terms = [
            'advanced', 'expert', 'professional', 'specialization',
            'master', 'in-depth', 'deep dive', 'complex', 'intensive'
        ]
        
        if any(term in text for term in beginner_terms):
            return 'beginner'
        elif any(term in text for term in advanced_terms):
            return 'advanced'
        else:
            return 'intermediate'
    
    def scrape_all_sources(self, skill, max_per_source=3):
        """Scrape courses from all sources and return combined results."""
        all_courses = []
        
        try:
            # Free sources
            all_courses.extend(self.scrape_freecodecamp(skill, max_per_source))
            all_courses.extend(self.scrape_khanacademy(skill, max_per_source))
            all_courses.extend(self.scrape_w3schools(skill, max_per_source))
            all_courses.extend(self.scrape_mdn(skill, max_per_source))
            
            # Paid sources
            all_courses.extend(self.scrape_codecademy(skill, max_per_source))
        except Exception as e:
            print(f"Error during scraping for skill '{skill}': {e}")
        
        print(f"Found {len(all_courses)} courses for '{skill}' across all sources")
        return all_courses
    
    def save_courses_to_db(self, courses, skill_name):
        """Save scraped courses to the database."""
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
                        'proficiency_level': course_data['difficulty']
                    }
                )
                
                if created:
                    count += 1
                    print(f"Added: {course_data['title']}")
                
            except Exception as e:
                print(f"Error saving course {course_data['title']}: {e}")
        
        return count