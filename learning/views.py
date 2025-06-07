# learning/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from datetime import timedelta
import json

from .models import Course, CourseProgress, SavedResource, Achievement, UserAchievement
from .services.progress_service import ProgressService
from .forms import SavedResourceForm

@login_required
def learning_dashboard(request):
    # Get user's course progress
    course_progress = CourseProgress.objects.filter(user=request.user).select_related('course')
    
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
    
    # Get achievements data
    earned_achievements = UserAchievement.objects.filter(
        user=request.user
    ).select_related('achievement')
    
    # Add earned achievements to recent activity
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
    
    all_achievements = Achievement.objects.all()
    achievements_data = []
    
    for achievement in all_achievements:
        is_earned = earned_achievements.filter(achievement=achievement).exists()
        achievements_data.append({
            'achievement': achievement,
            'is_earned': is_earned
        })
    
    # ----------------- ANALYTICS DATA -----------------
    # Calculate key metrics for analytics
    total_courses = course_progress.count()
    completed_courses = course_progress.filter(status='completed').count()
    in_progress_courses = course_progress.filter(status='in_progress').count()
    paused_courses = course_progress.filter(status='paused').count()
    
    # Completion rate
    completion_rate = 0
    if total_courses > 0:
        completion_rate = int((completed_courses / total_courses) * 100)
        
    # Total learning hours
    total_hours = course_progress.aggregate(Sum('estimated_hours_spent'))['estimated_hours_spent__sum'] or 0
    
    # Average hours per course
    avg_hours_per_course = 0
    if total_courses > 0:
        avg_hours_per_course = round(total_hours / total_courses, 1)
    
    # Average time to complete
    avg_completion_days = 0
    completed_with_dates = course_progress.filter(
        status='completed', 
        date_started__isnull=False,
        date_completed__isnull=False
    )
    
    if completed_with_dates.exists():
        total_days = 0
        for progress in completed_with_dates:
            days = (progress.date_completed - progress.date_started).days
            if days < 1:  # Handle same-day completion
                days = 1
            total_days += days
        avg_completion_days = round(total_days / completed_with_dates.count(), 1)
    
    # Weekly learning hours (last 4 weeks)
    four_weeks_ago = timezone.now().date() - timedelta(days=28)
    weekly_hours_data = {
        'labels': [],
        'data': []
    }
    
    # Initialize data for 4 weeks
    for i in range(4):
        week_start = four_weeks_ago + timedelta(days=i*7)
        week_end = week_start + timedelta(days=6)
        week_label = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}"
        weekly_hours_data['labels'].append(week_label)
        weekly_hours_data['data'].append(0)
    
    # For each course progress, add hours to the appropriate week
    for progress in course_progress:
        if progress.estimated_hours_spent > 0:
            # If updated in the last 4 weeks, add to the appropriate week
            if progress.last_activity_date.date() >= four_weeks_ago:
                days_ago = (timezone.now().date() - progress.last_activity_date.date()).days
                week_index = min(3, days_ago // 7)  # 0-3 for the 4 weeks
                weekly_hours_data['data'][week_index] += float(progress.estimated_hours_spent)
    
    # Add sample data if no real data exists (for demo/testing)
    if sum(weekly_hours_data['data']) == 0:
        weekly_hours_data['data'] = [3.5, 2.0, 5.5, 4.0]  # Sample data
    
    weekly_hours_json = json.dumps(weekly_hours_data)
    
    # Learning by platform (course provider)
    platform_data = {
        'labels': [],
        'data': []
    }
    
    platforms = {}
    for progress in course_progress:
        platform = progress.course.instructor
        if platform not in platforms:
            platforms[platform] = 0
        platforms[platform] += float(progress.estimated_hours_spent)
    
    # Sort by hours spent
    sorted_platforms = sorted(platforms.items(), key=lambda x: x[1], reverse=True)
    
    # Add the sorted platforms to the chart data
    for platform, hours in sorted_platforms:
        platform_data['labels'].append(platform)
        platform_data['data'].append(round(hours, 1))
    
    # Add sample data if no real data exists (for demo/testing)
    if len(platform_data['labels']) == 0:
        platform_data['labels'] = ['Dr. Sarah Johnson', 'Mike Chen', 'Prof. Emily Davis', 'Jessica Park']
        platform_data['data'] = [10.5, 7.0, 5.5, 3.0]  # Sample data
    
    platform_json = json.dumps(platform_data)
    
    # Get all analytics data
    analytics_data = {
        'total_courses': total_courses,
        'completed_courses': completed_courses,
        'in_progress_courses': in_progress_courses,
        'paused_courses': paused_courses,
        'completion_rate': completion_rate,
        'total_hours': total_hours,
        'avg_hours_per_course': avg_hours_per_course,
        'avg_completion_days': avg_completion_days,
        'weekly_hours_json': weekly_hours_json,
        'platform_json': platform_json,
    }
    
    # -------------------- END ANALYTICS --------------------
    
    return render(request, 'learning/dashboard.html', {
        'course_progress': course_progress,
        'recent_activity': recent_activity,
        'achievements': achievements_data,
        'analytics_data': analytics_data,
    })

@login_required
def update_course_progress(request, course_id):
    """Update progress for a specific course"""
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        hours_spent = request.POST.get('hours_spent') if status in ['in_progress', 'completed'] else None
        
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
            hours_spent=hours_spent
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

    if already_tracking and progress_status == 'in_progress':
        # If already in progress, show a status update form instead of redirecting or asking if started
        if request.method == 'POST':
            status = request.POST.get('status')
            if status in ['in_progress', 'completed', 'quit']:
                progress.status = status
                progress.save()
                messages.success(request, f"Course status updated to {status.replace('_', ' ').title()}.")
                return redirect('learning:dashboard')
        return render(request, 'learning/update_progress.html', {
            'course': course,
            'progress': progress
        })

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

    if request.method == 'GET' and show_redirect and course.course_url:
        # Open the course in a new tab using JavaScript in the template
        pass  # The template already handles this with window.open

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
            return redirect('learning:resource_library')
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
            return redirect('learning:resource_library')
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
        return redirect('learning:resource_library')
    
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
    
    # Get total number of courses enrolled
    total_courses = CourseProgress.objects.filter(user=request.user).count()
    
    for achievement in all_achievements:
        if not earned_achievements.filter(achievement=achievement).exists():
            # Calculate progress percentage
            progress = 0
            if achievement.requirement_type == 'courses_completed':
                progress = min(100, (completed_courses / achievement.requirement_value) * 100)
            elif achievement.requirement_type == 'skill_level':
                # Now using total courses instead of skills
                progress = min(100, (total_courses / achievement.requirement_value) * 100)
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
def course_redirect(request, course_id):
    """
    Redirect to external course URL and track course start
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Create or update progress record to track that user started the course
    progress, created = CourseProgress.objects.get_or_create(
        user=request.user, 
        course=course,
        defaults={
            'status': 'in_progress',
            'estimated_hours_spent': 0,
            'date_started': timezone.now(),
            'date_completed': None
        }
    )
    
    # If it was already created but not started, mark as in_progress
    if not created and progress.status == 'not_started':
        progress.status = 'in_progress'
        progress.date_started = timezone.now()
        progress.save()
    
    # If course has an external URL, redirect there
    if course.course_url:
        return redirect(course.course_url)
    else:
        # Fallback to internal course detail if no external URL
        messages.info(request, f"Added '{course.title}' to your learning dashboard")
        return redirect('learning:course_detail', course_id=course.id)

@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    # Get or create progress record - don't fail if it doesn't exist
    progress, created = CourseProgress.objects.get_or_create(
        user=request.user, 
        course=course,
        defaults={
            'status': 'not_started',
            'estimated_hours_spent': 0,
            'date_started': None,
            'date_completed': None
        }
    )
    # Get note history
    notes_history = progress.notes_history.all()
    return render(request, 'learning/course_detail.html', {
        'course': course,
        'progress': progress,
        'notes_history': notes_history
    })

@login_required
def dream_path(request):
    """
    Dream Path view - Shows personalized course recommendations based on user's dream role
    and provides career path guidance.
    """
    user = request.user
    
    # Handle dream role selection
    if request.method == 'POST':
        selected_dream_role = request.POST.get('dream_role')
        if selected_dream_role:
            user.dream_role = selected_dream_role
            user.save()
            messages.success(request, f"Updated your dream role to: {selected_dream_role}")
    
    # Get user's dream role (fallback to current role if not set)
    dream_role = user.dream_role.lower() if user.dream_role else (user.current_role.lower() if user.current_role else '')
    
    # Define available career paths
    available_paths = {
        'frontend_developer': {
            'title': 'Frontend Developer Path',
            'description': 'Master modern frontend technologies and build amazing user interfaces',
            'skills': ['HTML/CSS', 'JavaScript', 'React', 'Vue.js', 'TypeScript', 'UI/UX Design'],
            'next_roles': ['Senior Frontend Developer', 'Full Stack Developer', 'UI/UX Designer']
        },
        'backend_developer': {
            'title': 'Backend Developer Path', 
            'description': 'Build robust server-side applications and APIs',
            'skills': ['Python', 'Node.js', 'Database Design', 'API Development', 'Cloud Services'],
            'next_roles': ['Senior Backend Developer', 'DevOps Engineer', 'Solution Architect']
        },
        'fullstack_developer': {
            'title': 'Full Stack Developer Path',
            'description': 'Master both frontend and backend development',
            'skills': ['JavaScript', 'Python', 'React', 'Node.js', 'Database Design', 'DevOps'],
            'next_roles': ['Senior Full Stack Developer', 'Technical Lead', 'Solution Architect']
        },
        'data_scientist': {
            'title': 'Data Scientist Path',
            'description': 'Analyze data and build machine learning models',
            'skills': ['Python', 'Machine Learning', 'Data Analysis', 'Statistics', 'SQL'],
            'next_roles': ['Senior Data Scientist', 'ML Engineer', 'Data Engineering Lead']
        },
        'python_developer': {
            'title': 'Python Developer Path',
            'description': 'Master Python for web development, automation, and data science',
            'skills': ['Python', 'Django/Flask', 'Data Analysis', 'Automation', 'API Development'],
            'next_roles': ['Senior Python Developer', 'Data Scientist', 'Backend Lead']
        },
        'javascript_developer': {
            'title': 'JavaScript Developer Path',
            'description': 'Build modern web applications with JavaScript',
            'skills': ['JavaScript', 'React', 'Node.js', 'TypeScript', 'Web APIs'],
            'next_roles': ['Senior JavaScript Developer', 'Frontend Lead', 'Full Stack Developer']
        },
        'mobile_developer': {
            'title': 'Mobile Developer Path',
            'description': 'Create mobile applications for iOS and Android',
            'skills': ['React Native', 'Flutter', 'Swift', 'Kotlin', 'Mobile UI/UX'],
            'next_roles': ['Senior Mobile Developer', 'Mobile Architect', 'Product Manager']
        },
        'devops_engineer': {
            'title': 'DevOps Engineer Path',
            'description': 'Automate deployment, scaling, and management of applications',
            'skills': ['Docker', 'Kubernetes', 'AWS/Azure', 'CI/CD', 'Infrastructure as Code'],
            'next_roles': ['Senior DevOps Engineer', 'Cloud Architect', 'Platform Engineer']
        },
        'ui_ux_designer': {
            'title': 'UI/UX Designer Path',
            'description': 'Design beautiful and user-friendly interfaces',
            'skills': ['Figma', 'User Research', 'Prototyping', 'Design Systems', 'Accessibility'],
            'next_roles': ['Senior UX Designer', 'Design Lead', 'Product Designer']
        }
    }
    
    # Default path if role not found
    default_path = {
        'title': 'General Tech Career Path',
        'description': 'Start your tech journey with foundational programming skills',
        'skills': ['Programming Fundamentals', 'Web Development', 'Database Basics', 'Git/GitHub'],
        'next_roles': ['Frontend Developer', 'Backend Developer', 'Data Analyst']
    }
    
    # Find matching path based on dream role
    selected_path = default_path
    selected_dream_role_key = None
    
    # Try exact match first
    if dream_role in available_paths:
        selected_path = available_paths[dream_role]
        selected_dream_role_key = dream_role
    else:
        # Try partial matches
        for role_key, path_data in available_paths.items():
            if any(keyword in dream_role for keyword in role_key.replace('_', ' ').split()) or \
               any(keyword in role_key for keyword in dream_role.split()):
                selected_path = path_data
                selected_dream_role_key = role_key
                break
    
    # Get all courses and filter relevant ones
    all_courses = Course.objects.all()
    
    # Get recommended courses based on role
    recommended_courses = []
    beginner_courses = []
    advanced_courses = []
    
    for course in all_courses:
        course_title_lower = course.title.lower()
        course_desc_lower = course.description.lower()
        
        # Check if course matches user's path
        is_relevant = False
        for skill in selected_path['skills']:
            skill_lower = skill.lower()
            # Split skill into individual words for better matching
            skill_words = skill_lower.replace('/', ' ').split()
            if (skill_lower in course_title_lower or 
                skill_lower in course_desc_lower or
                any(word in course_title_lower or word in course_desc_lower for word in skill_words if len(word) > 2)):
                is_relevant = True
                break
        
        # Also include generally relevant programming/tech courses
        tech_keywords = ['programming', 'development', 'software', 'web', 'app', 'technology', 'computer']
        if not is_relevant and any(keyword in course_title_lower or keyword in course_desc_lower for keyword in tech_keywords):
            is_relevant = True
        
        if is_relevant:
            # Categorize by difficulty level
            if any(word in course_title_lower for word in ['beginner', 'intro', 'basic', 'fundamentals']):
                beginner_courses.append(course)
            elif any(word in course_title_lower for word in ['advanced', 'expert', 'master', 'deep']):
                advanced_courses.append(course)
            else:
                recommended_courses.append(course)
    
    # Get user's current progress
    user_progress = CourseProgress.objects.filter(user=user).select_related('course')
    completed_course_ids = user_progress.filter(status='completed').values_list('course_id', flat=True)
    in_progress_course_ids = user_progress.filter(status='in_progress').values_list('course_id', flat=True)
    
    # Calculate progress metrics
    total_recommended = len(recommended_courses) + len(beginner_courses) + len(advanced_courses)
    completed_recommended = len([c for c in recommended_courses + beginner_courses + advanced_courses 
                                if c.id in completed_course_ids])
    
    progress_percentage = 0
    if total_recommended > 0:
        progress_percentage = int((completed_recommended / total_recommended) * 100)
    
    # Calculate stroke-dashoffset for progress ring (circumference = 2 * π * radius = 2 * π * 56 ≈ 351.86)
    circumference = 351.86
    stroke_dashoffset = circumference - (progress_percentage / 100 * circumference)
    
    context = {
        'selected_path': selected_path,
        'available_paths': available_paths,
        'selected_dream_role_key': selected_dream_role_key,
        'current_dream_role': user.dream_role or 'Not set',
        'recommended_courses': recommended_courses[:6],  # Limit to 6 courses
        'beginner_courses': beginner_courses[:4],        # Limit to 4 courses
        'advanced_courses': advanced_courses[:4],        # Limit to 4 courses
        'user_progress': user_progress,
        'completed_course_ids': list(completed_course_ids),
        'in_progress_course_ids': list(in_progress_course_ids),
        'progress_percentage': progress_percentage,
        'stroke_dashoffset': stroke_dashoffset,
        'total_recommended': total_recommended,
        'completed_recommended': completed_recommended,
        'current_role': user.current_role or 'Getting Started',
    }
    
    return render(request, 'learning/dream_path.html', context)