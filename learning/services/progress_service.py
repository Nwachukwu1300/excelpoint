# learning/services/progress_service.py
from django.utils import timezone
from django.db.models import Count, Sum
from ..models import CourseProgress, LearningStreak, Achievement, UserAchievement
from skills.models import UserSkill

class ProgressService:
    @staticmethod
    def update_course_progress(user, course, status, hours_spent=None, notes=None):
        """Update course progress and related metrics"""
        # Get or create course progress
        progress, created = CourseProgress.objects.get_or_create(
            user=user,
            course=course,
            defaults={
                'status': status,
                'estimated_hours_spent': hours_spent or 0,
                'notes': notes or ''
            }
        )
        
        if not created:
            # Update existing progress
            progress.status = status
            if hours_spent is not None:
                progress.estimated_hours_spent = hours_spent
            if notes is not None:
                progress.notes = notes
            progress.save()
        
        # Update learning streak
        streak, _ = LearningStreak.objects.get_or_create(user=user)
        streak.update_streak()
        
        # Check and award achievements
        ProgressService.check_achievements(user)
        
        return progress
    
    @staticmethod
    def check_achievements(user):
        """Check and award achievements for a user"""
        # Get all achievements
        achievements = Achievement.objects.all()
        
        # Get user stats
        completed_courses = CourseProgress.objects.filter(
            user=user,
            status='completed'
        ).count()
        
        total_hours = CourseProgress.objects.filter(
            user=user
        ).aggregate(Sum('estimated_hours_spent'))['estimated_hours_spent__sum'] or 0
        
        streak = LearningStreak.objects.get(user=user)
        
        # Get total number of skills
        total_skills = UserSkill.objects.filter(user=user).count()
        
        # Check each achievement
        for achievement in achievements:
            # Skip if already earned
            if UserAchievement.objects.filter(user=user, achievement=achievement).exists():
                continue
            
            requirement_met = False
            
            if achievement.requirement_type == 'courses_completed':
                requirement_met = completed_courses >= achievement.requirement_value
            elif achievement.requirement_type == 'streak':
                requirement_met = streak.current_streak >= achievement.requirement_value
            elif achievement.requirement_type == 'skill_level':
                requirement_met = total_skills >= achievement.requirement_value
            elif achievement.requirement_type == 'total_hours':
                requirement_met = total_hours >= achievement.requirement_value
            
            if requirement_met:
                UserAchievement.objects.create(
                    user=user,
                    achievement=achievement
                )