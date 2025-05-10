from django.core.management.base import BaseCommand
from learning.models import Achievement

class Command(BaseCommand):
    help = 'Populates the achievements table with predefined achievements'

    def handle(self, *args, **kwargs):
        achievements = [
            {
                'name': 'First Steps',
                'description': 'Complete your first course',
                'requirement_type': 'courses_completed',
                'requirement_value': 1,
                'icon': '🎯'
            },
            {
                'name': 'Course Master',
                'description': 'Complete 5 courses',
                'requirement_type': 'courses_completed',
                'requirement_value': 5,
                'icon': '📚'
            },
            {
                'name': 'Learning Streak',
                'description': 'Maintain a 7-day learning streak',
                'requirement_type': 'streak',
                'requirement_value': 7,
                'icon': '🔥'
            },
            {
                'name': 'Dedicated Learner',
                'description': 'Maintain a 30-day learning streak',
                'requirement_type': 'streak',
                'requirement_value': 30,
                'icon': '🌟'
            },
            {
                'name': 'Skill Expert',
                'description': 'Achieve advanced level in 3 skills',
                'requirement_type': 'skill_level',
                'requirement_value': 3,
                'icon': '💪'
            },
            {
                'name': 'Master of Skills',
                'description': 'Achieve advanced level in 10 skills',
                'requirement_type': 'skill_level',
                'requirement_value': 10,
                'icon': '👑'
            },
            {
                'name': 'Time Investment',
                'description': 'Spend 50 hours learning',
                'requirement_type': 'total_hours',
                'requirement_value': 50,
                'icon': '⏰'
            },
            {
                'name': 'Learning Champion',
                'description': 'Spend 200 hours learning',
                'requirement_type': 'total_hours',
                'requirement_value': 200,
                'icon': '🏆'
            },
            {
                'name': 'Quick Starter',
                'description': 'Complete a course in less than a week',
                'requirement_type': 'courses_completed',
                'requirement_value': 1,
                'icon': '⚡'
            },
            {
                'name': 'Consistent Learner',
                'description': 'Complete 3 courses in a month',
                'requirement_type': 'courses_completed',
                'requirement_value': 3,
                'icon': '📅'
            }
        ]

        for achievement_data in achievements:
            Achievement.objects.get_or_create(
                name=achievement_data['name'],
                defaults={
                    'description': achievement_data['description'],
                    'requirement_type': achievement_data['requirement_type'],
                    'requirement_value': achievement_data['requirement_value'],
                    'icon': achievement_data['icon']
                }
            )

        self.stdout.write(self.style.SUCCESS('Successfully populated achievements')) 