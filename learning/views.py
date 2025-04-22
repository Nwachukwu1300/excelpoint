# learning/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Sum
from datetime import timedelta

from skills.models import Course, UserSkill
from .models import CourseProgress, LearningStreak, UserAchievement
from .services.progress_service import ProgressService

@login_required
def learning_dashboard(request):
    """Main learning dashboard showing progress and achievements"""
    # Get user's courses
    in_progress_courses = CourseProgress.objects.filter(
        user=request.user,
        status='in_progress'
    ).select_related('course')
    
    completed_courses = CourseProgress.objects.filter(
        user=request.user,
        status='completed'
    ).select_related('course')
    
    # Get streak data
    streak, created = LearningStreak.objects.get_or_create(user=request.user)
    
    # Get recent achievements
    recent_achievements = UserAchievement.objects.filter(
        user=request.user
    ).select_related('achievement').order_by('-date_earned')[:5]
    
    # Get skill progress
    user_skills = UserSkill.objects.filter(user=request.user)
    
    # Get progress stats
    progress_stats = {
        'completed_courses': completed_courses.count(),
        'in_progress_courses': in_progress_courses.count(),
        'total_hours': CourseProgress.objects.filter(
            user=request.user
        ).aggregate(hours=Sum('estimated_hours_spent'))['hours'] or 0,
        'skills_acquired': user_skills.count()
    }
    
    # Calculate skill acquisition over time (last 6 months)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=180)
    
    skill_acquisition = []
    current_date = start_date
    
    while current_date <= end_date:
        month_end = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        month_name = current_date.strftime('%b')
        
        skill_count = UserSkill.objects.filter(
            user=request.user,
            created_at__date__lte=month_end
        ).count()
        
        skill_acquisition.append({
            'month': month_name,
            'count': skill_count
        })
        
        # Move to next month
        current_date = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)
    
    return render(request, 'learning/dashboard.html', {
        'in_progress_courses': in_progress_courses,
        'completed_courses': completed_courses,
        'streak': streak,
        'recent_achievements': recent_achievements,
        'progress_stats': progress_stats,
        'skill_acquisition': skill_acquisition,
        'user_skills': user_skills
    })

@login_required
def update_course_progress(request, course_id):
    """Update progress for a specific course"""
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        progress_percent = request.POST.get('progress_percent')
        hours_spent = request.POST.get('hours_spent')
        notes = request.POST.get('notes')
        
        # Validate input
        if progress_percent:
            try:
                progress_percent = int(progress_percent)
                if progress_percent < 0 or progress_percent > 100:
                    messages.error(request, "Progress percentage must be between 0 and 100")
                    return redirect('learning:update_progress', course_id=course_id)
            except ValueError:
                messages.error(request, "Invalid progress percentage")
                return redirect('learning:update_progress', course_id=course_id)
        
        if hours_spent:
            try:
                hours_spent = float(hours_spent)
                if hours_spent < 0:
                    messages.error(request, "Hours spent cannot be negative")
                    return redirect('learning:update_progress', course_id=course_id)
            except ValueError:
                messages.error(request, "Invalid hours value")
                return redirect('learning:update_progress', course_id=course_id)
        
        # Update progress
        ProgressService.update_course_progress(
            user=request.user,
            course=course,
            status=status,
            progress_percent=progress_percent,
            hours_spent=hours_spent,
            notes=notes
        )
        
        messages.success(request, f"Progress updated for {course.title}")
        return redirect('learning:dashboard')
    
    # Get current progress
    try:
        progress = CourseProgress.objects.get(user=request.user, course=course)
    except CourseProgress.DoesNotExist:
        progress = None
    
    return render(request, 'learning/update_progress.html', {
        'course': course,
        'progress': progress
    })

@login_required
def achievements(request):
    """View all achievements and progress"""
    # Get user's earned achievements
    earned_achievements = UserAchievement.objects.filter(
        user=request.user
    ).select_related('achievement')
    
    # Get all achievements
    all_achievements = Achievement.objects.all()
    
    # Calculate progress for unearned achievements
    unearned_achievements = []
    
    for achievement in all_achievements:
        if not earned_achievements.filter(achievement=achievement).exists():
            progress = 0
            
            if achievement.requirement_type == 'courses_completed':
                completed_count = CourseProgress.objects.filter(
                    user=request.user, 
                    status='completed'
                ).count()
                progress = min(100, int(completed_count / achievement.requirement_value * 100))
                
            elif achievement.requirement_type == 'streak':
                try:
                    streak = LearningStreak.objects.get(user=request.user)
                    progress = min(100, int(streak.current_streak / achievement.requirement_value * 100))
                except LearningStreak.DoesNotExist:
                    progress = 0
                    
            elif achievement.requirement_type == 'skill_level':
                advanced_skills = UserSkill.objects.filter(
                    user=request.user,
                    proficiency_level='advanced'
                ).count()
                progress = min(100, int(advanced_skills / achievement.requirement_value * 100))
            
            unearned_achievements.append({
                'achievement': achievement,
                'progress': progress
            })
    
    return render(request, 'learning/achievements.html', {
        'earned_achievements': earned_achievements,
        'unearned_achievements': unearned_achievements
    })

@login_required
def track_course(request, course_id):
    """Start tracking a course (add to in-progress)"""
    course = get_object_or_404(Course, id=course_id)
    
    # Add the course to the user's in-progress list
    ProgressService.update_course_progress(
        user=request.user,
        course=course,
        status='in_progress',
        progress_percent=0
    )
    
    messages.success(request, f"Added '{course.title}' to your learning dashboard")
    return redirect('learning:dashboard')