from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import (
    UserProfileForm,
    UserAchievementForm,
    UserCertificationForm,
    UserEducationForm,
)
from .models import UserProfile, UserAchievement, UserCertification, UserEducation
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from datetime import timedelta
from learning.models import CourseProgress, UserAchievement as LearningUserAchievement
import logging

# Import Google OAuth service with error handling
try:
    from .services import GoogleOAuthService
    GOOGLE_OAUTH_AVAILABLE = True
except (ImportError, ValueError) as e:
    GOOGLE_OAUTH_AVAILABLE = False
    logging.warning(f"Google OAuth not available: {e}")

logger = logging.getLogger(__name__)


def google_oauth_initiate(request):
    """
    Initiate Google OAuth flow.
    """
    if not GOOGLE_OAUTH_AVAILABLE:
        messages.error(request, "Google OAuth is not configured. Please contact the administrator.")
        return redirect('/app/login?error=google')
    
    try:
        oauth_service = GoogleOAuthService()
        authorization_url, state = oauth_service.get_authorization_url()
        request.session['google_oauth_state'] = state
        return redirect(authorization_url)
    except Exception as e:
        logger.error(f"Error initiating Google OAuth: {e}")
        messages.error(request, "Unable to connect to Google. Please try again later.")
        return redirect('/app/login?error=google')

def google_oauth_callback(request):
    """
    Handle Google OAuth callback.
    """
    if not GOOGLE_OAUTH_AVAILABLE:
        messages.error(request, "Google OAuth is not configured. Please contact the administrator.")
        return redirect('/app/login?error=google')
    
    # Reject callbacks we didn't start (login CSRF)
    expected_state = request.session.pop('google_oauth_state', None)
    if not expected_state or not constant_time_compare(expected_state, request.GET.get('state', '')):
        messages.error(request, "Invalid login attempt. Please try again.")
        return redirect('/app/login?error=google')

    try:
        # Get authorization code from request
        authorization_code = request.GET.get('code')
        if not authorization_code:
            messages.error(request, "Authorization code not received from Google.")
            return redirect('/app/login?error=google')
        
        # Exchange code for token
        oauth_service = GoogleOAuthService()
        credentials = oauth_service.exchange_code_for_token(authorization_code)
        
        # Get user info from Google
        user_info = oauth_service.get_user_info(credentials)
        
        # Authenticate or create user
        user = oauth_service.authenticate_or_create_user(user_info)
        
        if user:
            # Log the user in
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")

            return redirect('app')
        else:
            messages.error(request, "Unable to authenticate with Google. Please try again.")
            return redirect('/app/login?error=google')
            
    except Exception as e:
        logger.error(f"Error in Google OAuth callback: {e}")
        messages.error(request, "Authentication failed. Please try again or use email login.")
        return redirect('/app/login?error=google')


def calculate_profile_completion(user):
    """
    Calculates the percentage of profile completion.
    
    Parameters:
        user: User instance to check profile completion
        
    Returns:
        float: Percentage of profile completion (0-100)
    """
    # Fields to check for completion
    fields = ['current_role', 'bio', 'experience_level']
    
    # Count filled fields (not empty or null)
    filled_fields = sum(1 for field in fields if getattr(user, field, None))
    
    # Calculate percentage
    return round((filled_fields / len(fields)) * 100, 2)


@login_required
def logout_user(request):
    """
    Handles the logout process:
    - GET: Show logout confirmation page
    - POST: Process logout and redirect to home
    """
    if request.method == 'POST':
        try:
            logout(request)
            messages.success(request, 'You have been successfully logged out.')
            return redirect('home')
        except Exception as e:
            messages.error(request, f'Logout failed: {str(e)}')
            return redirect('users:profile')
    else:
        # GET request: show the logout confirmation page
        return render(request, 'users/logout.html')




@login_required
def profile(request):
    """Display user profile with learning stats and achievements"""
    # Get user's learning stats
    completed_courses = CourseProgress.objects.filter(
        user=request.user,
        status='completed'
    ).count()
    
    # Calculate profile completion percentage
    profile_completion = calculate_profile_completion(request.user)
    
    # Get recent activity - ensure we're only getting current user's data
    recent_activity = []
    
    # Make sure we have fresh data for this user
    current_time = timezone.now()
    thirty_days_ago = current_time - timedelta(days=30)
    
    # Add course progress updates - strictly filter by current user
    recent_progress = CourseProgress.objects.filter(
        user=request.user,
        last_activity_date__gte=thirty_days_ago
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
    
    # Add earned achievements - strictly filter by current user
    earned_achievements = LearningUserAchievement.objects.filter(
        user=request.user
    ).select_related('achievement')
    
    for user_achievement in earned_achievements:
        if user_achievement.date_earned >= thirty_days_ago:
            recent_activity.append({
                'icon': user_achievement.achievement.icon,
                'title': f"Earned {user_achievement.achievement.name}",
                'description': user_achievement.achievement.description,
                'timestamp': user_achievement.date_earned
            })
    
    # Sort recent activity by timestamp
    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Get recent achievements
    recent_achievements = earned_achievements.order_by('-date_earned')[:3]
    achievements_count = earned_achievements.count()
    
    # Count enrolled courses
    enrolled_courses = CourseProgress.objects.filter(user=request.user).count()
    
    return render(request, 'users/profile.html', {
        'completed_courses': completed_courses,
        'profile_completion': profile_completion,
        'recent_activity': recent_activity,
        'recent_achievements': recent_achievements,
        'achievements_count': achievements_count,
        'enrolled_courses': enrolled_courses
    })

@login_required
def edit_profile(request):
    """
    View for editing user profile information.
    """
    if request.method == 'POST':
        # The form edits User fields, so it must be bound to the User, not the profile
        profile_form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('users:profile')
    else:
        profile_form = UserProfileForm(instance=request.user)

    return render(request, 'users/edit_profile.html', {
        'profile_form': profile_form
    })

@login_required
def manage_achievements(request):
    """
    View for managing user achievements and awards.
    Displays a list of existing achievements and a form to add new ones.
    """
    user = request.user
    achievements = user.user_achievements.all().order_by('-date_added')
    
    if request.method == 'POST':
        form = UserAchievementForm(request.POST)
        if form.is_valid():
            achievement = form.save(commit=False)
            achievement.user = user
            achievement.save()
            messages.success(request, 'Achievement added successfully!')
            return redirect('users:manage_achievements')
    else:
        form = UserAchievementForm()
    
    return render(request, 'users/manage_achievements.html', {
        'achievements': achievements,
        'form': form
    })

@login_required
def edit_achievement(request, achievement_id):
    """
    View for editing an existing achievement.
    """
    achievement = get_object_or_404(UserAchievement, id=achievement_id, user=request.user)
    
    if request.method == 'POST':
        form = UserAchievementForm(request.POST, instance=achievement)
        if form.is_valid():
            form.save()
            messages.success(request, 'Achievement updated successfully!')
            return redirect('users:manage_achievements')
    else:
        form = UserAchievementForm(instance=achievement)
    
    return render(request, 'users/edit_achievement.html', {
        'form': form,
        'achievement': achievement
    })

@login_required
def delete_achievement(request, achievement_id):
    """
    View for deleting an achievement.
    """
    achievement = get_object_or_404(UserAchievement, id=achievement_id, user=request.user)
    
    if request.method == 'POST':
        achievement.delete()
        messages.success(request, 'Achievement deleted successfully!')
        return redirect('users:manage_achievements')
    
    return render(request, 'users/delete_achievement.html', {
        'achievement': achievement
    })

@login_required
def manage_certifications(request):
    """
    View for managing user certifications.
    """
    if request.method == 'POST':
        form = UserCertificationForm(request.POST)
        if form.is_valid():
            certification = form.save(commit=False)
            certification.user = request.user
            certification.save()
            messages.success(request, 'Certification added successfully!')
            return redirect('users:manage_certifications')
    else:
        form = UserCertificationForm()
    
    # Get user's certifications
    certifications = UserCertification.objects.filter(user=request.user)
    
    return render(request, 'users/manage_certifications.html', {
        'form': form,
        'certifications': certifications
    })

@login_required
def edit_certification(request, certification_id):
    """
    View for editing an existing certification.
    """
    certification = get_object_or_404(UserCertification, id=certification_id, user=request.user)
    
    if request.method == 'POST':
        form = UserCertificationForm(request.POST, instance=certification)
        if form.is_valid():
            form.save()
            messages.success(request, 'Certification updated successfully!')
            return redirect('users:manage_certifications')
    else:
        form = UserCertificationForm(instance=certification)
    
    return render(request, 'users/edit_certification.html', {
        'form': form,
        'certification': certification
    })

@login_required
def delete_certification(request, certification_id):
    """
    View for deleting a certification.
    """
    certification = get_object_or_404(UserCertification, id=certification_id, user=request.user)
    
    if request.method == 'POST':
        certification.delete()
        messages.success(request, 'Certification deleted successfully!')
        return redirect('users:manage_certifications')
    
    return render(request, 'users/delete_certification.html', {
        'certification': certification
    })

@login_required
def manage_education(request):
    """
    View for managing user education.
    """
    if request.method == 'POST':
        form = UserEducationForm(request.POST)
        if form.is_valid():
            education = form.save(commit=False)
            education.user = request.user
            education.save()
            messages.success(request, 'Education entry added successfully!')
            return redirect('users:manage_education')
    else:
        form = UserEducationForm()
    
    # Get user's education entries
    education_entries = UserEducation.objects.filter(user=request.user)
    
    return render(request, 'users/manage_education.html', {
        'form': form,
        'education_entries': education_entries
    })

@login_required
def edit_education(request, education_id):
    """
    View for editing an existing education entry.
    """
    education = get_object_or_404(UserEducation, id=education_id, user=request.user)
    
    if request.method == 'POST':
        form = UserEducationForm(request.POST, instance=education)
        if form.is_valid():
            form.save()
            messages.success(request, 'Education entry updated successfully!')
            return redirect('users:manage_education')
    else:
        form = UserEducationForm(instance=education)
    
    return render(request, 'users/edit_education.html', {
        'form': form,
        'education': education
    })

@login_required
def delete_education(request, education_id):
    """
    View for deleting an education entry.
    """
    education = get_object_or_404(UserEducation, id=education_id, user=request.user)
    
    if request.method == 'POST':
        education.delete()
        messages.success(request, 'Education entry deleted successfully!')
        return redirect('users:manage_education')
    
    return render(request, 'users/delete_education.html', {
        'education': education
    })
