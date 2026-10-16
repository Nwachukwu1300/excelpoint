from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import resolve

from config.views import get_recent_activity
from learning.models import Course, CourseProgress


class RecentActivityLinksTest(TestCase):
    def test_course_activity_links_resolve(self):
        user = get_user_model().objects.create_user('u', password='p')
        course = Course.objects.create(title='C', description='d', instructor='i', course_url='https://x.com')
        CourseProgress.objects.create(user=user, course=course, status='in_progress')

        urls = [a['url'] for a in get_recent_activity(user) if a['type'] == 'course_progress']

        self.assertEqual(len(urls), 1)
        self.assertEqual(resolve(urls[0]).view_name, 'learning:course_detail')
