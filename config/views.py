from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q, Avg

from learning.models import Course, CourseProgress, Achievement, UserAchievement
from subjects.models import Subject, SubjectMaterial, UserQuizAttempt


def home(request):
    """
    Home page view that provides personalized content for authenticated users
    and marketing content for non-authenticated users.
    """
    if request.user.is_authenticated:
        return authenticated_home(request)
    else:
        return marketing_home(request)


def authenticated_home(request):
    """Home page for authenticated users with personalized content."""
    
    # Get user's recent activity
    recent_activity = get_recent_activity(request.user)
    
    # Get user's progress data
    progress_data = get_progress_data(request.user)
    
    # Get user's subjects and materials
    user_subjects = Subject.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Get recent quiz attempts
    recent_quizzes = UserQuizAttempt.objects.filter(
        user=request.user
    ).select_related('quiz', 'quiz__subject').order_by('-start_time')[:5]
    

    
    # Get user's achievements
    user_achievements = UserAchievement.objects.filter(
        user=request.user
    ).select_related('achievement').order_by('-date_earned')[:3]
    
    # Get course progress
    course_progress = CourseProgress.objects.filter(
        user=request.user
    ).select_related('course').order_by('-last_activity_date')[:3]
    
    context = {
        'recent_activity': recent_activity,
        'progress_data': progress_data,
        'user_subjects': user_subjects,
        'recent_quizzes': recent_quizzes,
        'user_achievements': user_achievements,
        'course_progress': course_progress,
        'total_subjects': Subject.objects.filter(user=request.user).count(),
        'total_materials': SubjectMaterial.objects.filter(subject__user=request.user).count(),
        'total_quizzes_taken': UserQuizAttempt.objects.filter(user=request.user).count(),

    }
    
    return render(request, 'home.html', context)


def marketing_home(request):
    """Marketing home page for non-authenticated users."""
    return render(request, 'home.html', {})


def get_recent_activity(user):
    """Get user's recent activity across all features."""
    activities = []
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # Recent course progress
    recent_progress = CourseProgress.objects.filter(
        user=user,
        last_activity_date__gte=thirty_days_ago
    ).select_related('course')
    
    for progress in recent_progress:
        activities.append({
            'type': 'course_progress',
            'icon': '📚',
            'title': f"Updated progress on {progress.course.title}",
            'description': f"Status: {progress.get_status_display()}",
            'timestamp': progress.last_activity_date,
            'url': f"/learning/course/{progress.course.id}/"
        })
    
    # Recent quiz attempts (using new UserQuizAttempt model)
    recent_quiz_attempts = UserQuizAttempt.objects.filter(
        user=user,
        start_time__gte=thirty_days_ago
    ).select_related('quiz', 'quiz__subject')
    
    for attempt in recent_quiz_attempts:
        activities.append({
            'type': 'quiz_attempt',
            'icon': '🧠',
            'title': f"Took quiz: {attempt.quiz.title}",
            'description': f"Score: {attempt.score}%",
            'timestamp': attempt.start_time,
            'url': f"/subjects/{attempt.quiz.subject.id}/"
        })
    

    
    # Recent achievements
    recent_achievements = UserAchievement.objects.filter(
        user=user,
        date_earned__gte=thirty_days_ago
    ).select_related('achievement')
    
    for user_achievement in recent_achievements:
        activities.append({
            'type': 'achievement',
            'icon': '🏆',
            'title': f"Earned: {user_achievement.achievement.name}",
            'description': user_achievement.achievement.description,
            'timestamp': user_achievement.date_earned,
            'url': "/learning/achievements/"
        })
    
    # Sort by timestamp and return top 10
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    return activities[:10]


def get_progress_data(user):
    """Get user's learning progress statistics."""
    
    # Course progress
    course_progress = CourseProgress.objects.filter(user=user)
    total_courses = course_progress.count()
    completed_courses = course_progress.filter(status='completed').count()
    in_progress_courses = course_progress.filter(status='in_progress').count()
    
    # Subject and material stats
    total_subjects = Subject.objects.filter(user=user).count()
    total_materials = SubjectMaterial.objects.filter(subject__user=user).count()
    
    # Quiz stats
    quiz_attempts = UserQuizAttempt.objects.filter(user=user)
    total_quizzes_taken = quiz_attempts.count()
    average_quiz_score = 0
    if total_quizzes_taken > 0:
        average_quiz_score = round(quiz_attempts.aggregate(avg_score=Avg('score'))['avg_score'] or 0, 1)
    
    # Achievement stats
    total_achievements = UserAchievement.objects.filter(user=user).count()
    all_achievements = Achievement.objects.count()
    achievement_percentage = 0
    if all_achievements > 0:
        achievement_percentage = round((total_achievements / all_achievements) * 100, 1)
    
    return {
        'total_courses': total_courses,
        'completed_courses': completed_courses,
        'in_progress_courses': in_progress_courses,
        'completion_rate': round((completed_courses / total_courses * 100) if total_courses > 0 else 0, 1),
        'total_subjects': total_subjects,
        'total_materials': total_materials,
        'total_quizzes_taken': total_quizzes_taken,
        'average_quiz_score': average_quiz_score,
        'total_achievements': total_achievements,
        'achievement_percentage': achievement_percentage,
    } 