from django.shortcuts import render, redirect, get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import UserSerializer
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from .forms import RegistrationForm, UserProfileForm, UserAchievementForm, UserCertificationForm, UserEducationForm
from .models import User, UserProfile, UserAchievement, UserCertification, UserEducation
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from learning.models import CourseProgress, UserAchievement as LearningUserAchievement
import json
import logging

# Import Google OAuth service with error handling
try:
    from .services import GoogleOAuthService, GoogleOAuthBackend
    GOOGLE_OAUTH_AVAILABLE = True
except (ImportError, ValueError) as e:
    GOOGLE_OAUTH_AVAILABLE = False
    logging.warning(f"Google OAuth not available: {e}")

logger = logging.getLogger(__name__)


def register_user(request):
   """
   Registration endpoint.
   GET: Shows registration form
   POST: Creates new user
   """
   if request.user.is_authenticated:
       # If already logged in, redirect to profile page
       return redirect('users:profile')
       
   if request.method == 'POST':
       form = RegistrationForm(request.POST)
       if form.is_valid():
           # Create the user account
           user = form.save()
           # Log the user in
           login(request, user)
           messages.success(request, 'Your account has been created successfully! Welcome to ExcelPoint.')
           return redirect('home')
   else:
       # GET request: show registration form
       form = RegistrationForm()
   
   return render(request, 'users/register.html', {'form': form})


def google_oauth_initiate(request):
    """
    Initiate Google OAuth flow.
    """
    if not GOOGLE_OAUTH_AVAILABLE:
        messages.error(request, "Google OAuth is not configured. Please contact the administrator.")
        return redirect('users:login')
    
    try:
        oauth_service = GoogleOAuthService()
        authorization_url = oauth_service.get_authorization_url()
        return redirect(authorization_url)
    except Exception as e:
        logger.error(f"Error initiating Google OAuth: {e}")
        messages.error(request, "Unable to connect to Google. Please try again later.")
        return redirect('users:login')

def google_oauth_callback(request):
    """
    Handle Google OAuth callback.
    """
    if not GOOGLE_OAUTH_AVAILABLE:
        messages.error(request, "Google OAuth is not configured. Please contact the administrator.")
        return redirect('users:login')
    
    try:
        # Get authorization code from request
        authorization_code = request.GET.get('code')
        if not authorization_code:
            messages.error(request, "Authorization code not received from Google.")
            return redirect('users:login')
        
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
            
            # Redirect to dashboard or next page
            next_url = request.GET.get('next', 'learning:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, "Unable to authenticate with Google. Please try again.")
            return redirect('users:login')
            
    except Exception as e:
        logger.error(f"Error in Google OAuth callback: {e}")
        messages.error(request, "Authentication failed. Please try again or use email login.")
        return redirect('users:login')


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def login_user(request):
    """
    Handles user login.
    - GET: Show login form
    - POST: Process login request
    """
    if request.user.is_authenticated:
        # If already logged in, redirect to profile page
        return redirect('users:profile')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, 'Both username and password are required')
            return render(request, 'users/login.html')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, 'Login successful!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
    
    # If GET request or login failed
    return render(request, 'users/login.html')

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




@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Updates the profile of the currently logged-in user.
    GET: View profile data for editing
    PUT: Save profile changes
    """
    if request.method == 'GET':
        try:
            user = request.user
            serializer = UserSerializer(user)
            return Response({
                'status': 'success',
                'profile': serializer.data,
                'update_template': {
                    'current_role': user.current_role or 'enter_role',
                    'experience_level': user.experience_level,
                    'bio': user.bio or 'enter_bio',
                    'linkedin_profile': user.linkedin_profile or '',
                    'github_profile': user.github_profile or ''
                }
            })
        except Exception as e:
            return Response({
                'error': 'Failed to fetch profile',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif request.method == 'PUT':
        try:
            serializer = UserSerializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'status': 'success',
                    'message': 'Profile updated successfully',
                    'profile': serializer.data
                })
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Profile update failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'PUT', 'POST'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    Comprehensive profile endpoint.
    GET: View profile
    PUT: Update profile
    POST: Change password
    """
    if request.method == 'GET':
        try:
            user = request.user
            serializer = UserSerializer(user)
            
            return Response({
                'status': 'success',
                'profile_info': {
                    'details': serializer.data,
                    'completion_percentage': calculate_profile_completion(user),
                },
                'update_template': {
                    'current_role': 'enter_role',
                    'experience_level': 'entry/mid/senior',
                    'bio': 'enter_bio'
                },
                'password_change_template': {
                    'old_password': 'enter_current_password',
                    'new_password': 'enter_new_password'
                }
            })
            
        except Exception as e:
            return Response({
                'error': 'Failed to fetch profile',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == 'PUT':
        try:
            serializer = UserSerializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'status': 'success',
                    'message': 'Profile updated successfully',
                    'profile': serializer.data
                })
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Profile update failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == 'POST':
        try:
            if not request.user.check_password(request.data.get('old_password')):
                return Response({
                    'error': 'Current password is incorrect'
                }, status=status.HTTP_400_BAD_REQUEST)

            request.user.set_password(request.data.get('new_password'))
            request.user.save()
            
            return Response({
                'message': 'Password updated successfully'
            })
        except Exception as e:
            return Response({
                'error': 'Password change failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Allows users to change their password while logged in.
    """
    try:
        # Validate old password
        if not request.user.check_password(request.data.get('old_password')):
            return Response({
                'error': 'Current password is incorrect'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Set and validate new password
        request.user.set_password(request.data.get('new_password'))
        request.user.save()
        
        return Response({
            'message': 'Password updated successfully'
        })
    except Exception as e:
        return Response({
            'error': 'Password change failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    user = request.user
    
    # Initialize both forms
    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
        
        # Populate User model fields
        profile_form.fields['first_name'].initial = user.first_name
        profile_form.fields['last_name'].initial = user.last_name
        profile_form.fields['email'].initial = user.email
        profile_form.fields['current_role'].initial = user.current_role
        
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
    else:
        profile_form = UserProfileForm(instance=request.user.profile)
        
        # Populate User model fields
        profile_form.fields['first_name'].initial = user.first_name
        profile_form.fields['last_name'].initial = user.last_name
        profile_form.fields['email'].initial = user.email
        profile_form.fields['current_role'].initial = user.current_role
    
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