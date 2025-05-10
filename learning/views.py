# learning/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from datetime import timedelta

from skills.models import Course, UserSkill
from .models import CourseProgress, LearningStreak, SavedResource, Achievement, UserAchievement
from .services.progress_service import ProgressService
from .forms import SavedResourceForm

@login_required
def learning_dashboard(request):
    # Get user's course progress
    course_progress = CourseProgress.objects.filter(user=request.user).select_related('course')
    
    # Get learning streak
    streak, _ = LearningStreak.objects.get_or_create(user=request.user)
    
    # Get skill growth data for the last 6 months
    six_months_ago = timezone.now() - timedelta(days=180)
    skill_growth = UserSkill.objects.filter(
        user=request.user,
        created_at__gte=six_months_ago
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Format skill growth data for the chart
    skill_growth_data = {
        'labels': [],
        'data': []
    }
    
    # Ensure we have data for all months
    current_date = six_months_ago
    while current_date <= timezone.now():
        month_str = current_date.strftime('%Y-%m')
        skill_growth_data['labels'].append(month_str)
        skill_growth_data['data'].append(0)
        current_date += timedelta(days=32)
        current_date = current_date.replace(day=1)
    
    # Fill in actual data
    for item in skill_growth:
        month_str = item['month'].strftime('%Y-%m')
        if month_str in skill_growth_data['labels']:
            index = skill_growth_data['labels'].index(month_str)
            skill_growth_data['data'][index] = item['count']
    
    # Get achievements data
    earned_achievements = UserAchievement.objects.filter(
        user=request.user
    ).select_related('achievement')
    
    all_achievements = Achievement.objects.all()
    achievements_data = []
    
    for achievement in all_achievements:
        is_earned = earned_achievements.filter(achievement=achievement).exists()
        achievements_data.append({
            'achievement': achievement,
            'is_earned': is_earned
        })
    
    # Get recent activity
    recent_activity = []
    
    # Add course progress updates
    recent_progress = CourseProgress.objects.filter(
        user=request.user,
        last_activity_date__gte=timezone.now() - timedelta(days=30)
    ).select_related('course')
    
    for progress in recent_progress:
        icon = '📚'
        if progress.status == 'completed':
            title = f"Completed {progress.course.title}"
            icon = '🎉'
        else:
            title = f"Updated progress on {progress.course.title}"
        
        recent_activity.append({
            'icon': icon,
            'title': title,
            'description': f"Status: {progress.get_status_display()}",
            'timestamp': progress.last_activity_date
        })
    
    # Add earned achievements
    for user_achievement in earned_achievements:
        if user_achievement.date_earned >= timezone.now() - timedelta(days=30):
            recent_activity.append({
                'icon': user_achievement.achievement.icon,
                'title': f"Earned {user_achievement.achievement.name}",
                'description': user_achievement.achievement.description,
                'timestamp': user_achievement.date_earned
            })
    
    # Sort recent activity by timestamp
    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Get user's skills
    user_skills = UserSkill.objects.filter(user=request.user)
    skill_courses = []
    for user_skill in user_skills:
        courses = Course.objects.filter(
            courseskill__skill_name=user_skill.skill_name
        ).distinct()
        if courses.exists():
            skill_courses.append({
                'skill_name': user_skill.skill_name,
                'courses': courses
            })
    
    return render(request, 'learning/dashboard.html', {
        'course_progress': course_progress,
        'streak': streak,
        'skill_growth_data': skill_growth_data,
        'achievements': achievements_data,
        'recent_activity': recent_activity,
        'skill_courses': skill_courses,
    })

@login_required
def update_course_progress(request, course_id):
    """Update progress for a specific course"""
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        hours_spent = request.POST.get('hours_spent')
        notes = request.POST.get('notes')
        
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
def track_course(request, course_id):
    """Start tracking a course (add to in-progress)"""
    course = get_object_or_404(Course, id=course_id)
    
    # Add the course to the user's in-progress list
    ProgressService.update_course_progress(
        user=request.user,
        course=course,
        status='in_progress'
    )
    
    messages.success(request, f"Added '{course.title}' to your learning dashboard")
    return redirect('learning:dashboard')

@login_required
def confirm_course(request, course_id):
    """Show course confirmation page before starting to track a course"""
    course = get_object_or_404(Course, id=course_id)
    already_tracking = False
    progress_status = None
    session_key = f'course_redirected_{course_id}'
    show_redirect = False
    try:
        progress = CourseProgress.objects.get(user=request.user, course=course)
        progress_status = progress.status
        if progress.status != 'not_started':
            already_tracking = True
    except CourseProgress.DoesNotExist:
        # Create a not_started progress entry to track the view
        ProgressService.update_course_progress(
            user=request.user,
            course=course,
            status='not_started'
        )
        progress_status = 'not_started'
        progress = CourseProgress.objects.get(user=request.user, course=course)

    if request.method == 'POST':
        confirm = request.POST.get('confirm')
        if confirm == 'yes':
            # Mark as in_progress and redirect to update progress page
            progress.status = 'in_progress'
            progress.save()
            # Remove session flag so next time user starts this course, it will redirect again
            if session_key in request.session:
                del request.session[session_key]
            return redirect('learning:update_progress', course_id=course.id)
        elif confirm == 'no':
            # Remove not_started progress and redirect to dashboard
            if progress.status == 'not_started':
                progress.delete()
            if session_key in request.session:
                del request.session[session_key]
            return redirect('learning:dashboard')

    # On GET: only show redirect if not already done for this course in this session
    if not request.session.get(session_key, False):
        show_redirect = True
        request.session[session_key] = True

    return render(request, 'learning/course_confirmation.html', {
        'course': course,
        'already_tracking': already_tracking,
        'progress_status': progress_status,
        'show_redirect': show_redirect
    })

@login_required
def check_course_registration(request, course_id):
    """Check if user registered for a course after viewing it"""
    course = get_object_or_404(Course, id=course_id)
    
    try:
        progress = CourseProgress.objects.get(user=request.user, course=course)
        if progress.status != 'not_started':
            messages.info(request, f"You are already tracking '{course.title}'")
            return redirect('learning:dashboard')
            
        if request.method == 'POST':
            if 'register' in request.POST:
                # User registered for the course
                progress.status = 'in_progress'
                progress.save()
                messages.success(request, f"Added '{course.title}' to your learning dashboard")
            else:
                # User didn't register, remove the progress entry
                progress.delete()
                messages.info(request, f"Removed '{course.title}' from tracking")
            return redirect('learning:dashboard')
            
        return render(request, 'learning/course_registration_check.html', {
            'course': course
        })
    except CourseProgress.DoesNotExist:
        messages.error(request, "Course not found in your viewing history")
        return redirect('learning:dashboard')

@login_required
def resource_library(request):
    """View for displaying user's saved resources."""
    resources = SavedResource.objects.filter(user=request.user).order_by('-date_saved')
    return render(request, 'learning/resource_library.html', {
        'resources': resources
    })

@login_required
def add_resource(request):
    """View for adding a new resource."""
    if request.method == 'POST':
        form = SavedResourceForm(request.POST)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.user = request.user
            resource.save()
            messages.success(request, 'Resource saved successfully!')
            return redirect('resource_library')
    else:
        form = SavedResourceForm()
    
    return render(request, 'learning/add_resource.html', {
        'form': form
    })

@login_required
def edit_resource(request, resource_id):
    """View for editing an existing resource."""
    resource = get_object_or_404(SavedResource, id=resource_id, user=request.user)
    
    if request.method == 'POST':
        form = SavedResourceForm(request.POST, instance=resource)
        if form.is_valid():
            form.save()
            messages.success(request, 'Resource updated successfully!')
            return redirect('resource_library')
    else:
        form = SavedResourceForm(instance=resource)
    
    return render(request, 'learning/edit_resource.html', {
        'form': form,
        'resource': resource
    })

@login_required
def delete_resource(request, resource_id):
    """View for deleting a resource."""
    resource = get_object_or_404(SavedResource, id=resource_id, user=request.user)
    
    if request.method == 'POST':
        resource.delete()
        messages.success(request, 'Resource deleted successfully!')
        return redirect('resource_library')
    
    return render(request, 'learning/delete_resource.html', {
        'resource': resource
    })

@login_required
def achievements(request):
    """Display user's achievements and progress"""
    earned_achievements = UserAchievement.objects.filter(
        user=request.user
    ).select_related('achievement')
    
    # Get all achievements and calculate progress for unearned ones
    all_achievements = Achievement.objects.all()
    unearned_achievements = []
    
    # Get user stats for progress calculation
    completed_courses = CourseProgress.objects.filter(
        user=request.user,
        status='completed'
    ).count()
    
    total_hours = CourseProgress.objects.filter(
        user=request.user
    ).aggregate(Sum('estimated_hours_spent'))['estimated_hours_spent__sum'] or 0
    
    streak = LearningStreak.objects.get(user=request.user)
    
    # Get total number of skills
    total_skills = UserSkill.objects.filter(user=request.user).count()
    
    for achievement in all_achievements:
        if not earned_achievements.filter(achievement=achievement).exists():
            # Calculate progress percentage
            progress = 0
            if achievement.requirement_type == 'courses_completed':
                progress = min(100, (completed_courses / achievement.requirement_value) * 100)
            elif achievement.requirement_type == 'streak':
                progress = min(100, (streak.current_streak / achievement.requirement_value) * 100)
            elif achievement.requirement_type == 'skill_level':
                # Now using total skills instead of advanced skills
                progress = min(100, (total_skills / achievement.requirement_value) * 100)
            elif achievement.requirement_type == 'total_hours':
                progress = min(100, (total_hours / achievement.requirement_value) * 100)
            
            unearned_achievements.append({
                'achievement': achievement,
                'progress': int(progress)
            })
    
    return render(request, 'learning/achievements.html', {
        'earned_achievements': earned_achievements,
        'unearned_achievements': unearned_achievements
    })

@login_required
def recent_activity(request):
    """Display user's recent learning activity"""
    # Get recent activity
    recent_activity = []
    
    # Add course progress updates
    recent_progress = CourseProgress.objects.filter(
        user=request.user,
        last_activity_date__gte=timezone.now() - timedelta(days=30)
    ).select_related('course').order_by('-last_activity_date')
    
    for progress in recent_progress:
        icon = '📚'
        if progress.status == 'completed':
            title = f"Completed {progress.course.title}"
            icon = '🎉'
        else:
            title = f"Updated progress on {progress.course.title}"
        
        recent_activity.append({
            'icon': icon,
            'title': title,
            'description': f"Status: {progress.get_status_display()}",
            'timestamp': progress.last_activity_date
        })
    
    # Add earned achievements
    earned_achievements = UserAchievement.objects.filter(
        user=request.user,
        date_earned__gte=timezone.now() - timedelta(days=30)
    ).select_related('achievement').order_by('-date_earned')
    
    for user_achievement in earned_achievements:
        recent_activity.append({
            'icon': user_achievement.achievement.icon,
            'title': f"Earned {user_achievement.achievement.name}",
            'description': user_achievement.achievement.description,
            'timestamp': user_achievement.date_earned
        })
    
    # Sort all activity by timestamp
    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render(request, 'learning/recent_activity.html', {
        'recent_activity': recent_activity
    })

@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    progress = get_object_or_404(CourseProgress, user=request.user, course=course)
    # Get note history
    notes_history = progress.notes_history.all()
    return render(request, 'learning/course_detail.html', {
        'course': course,
        'progress': progress,
        'notes_history': notes_history
    })