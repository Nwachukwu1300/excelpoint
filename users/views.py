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
from .forms import RegistrationForm, UserProfileForm, CustomSkillForm, UserAchievementForm, UserCertificationForm, UserEducationForm
from skills.models import Skill
from .models import User, UserAchievement, UserCertification, UserEducation
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from learning.models import CourseProgress, LearningStreak, UserAchievement as LearningUserAchievement
from skills.models import UserSkill


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
           messages.success(request, 'Your account has been created successfully! Welcome to Career Nexus.')
           return redirect('home')
   else:
       # GET request: show registration form
       form = RegistrationForm()
   
   return render(request, 'users/register.html', {'form': form})



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
            
            # Get skill information
            skills_from_resume = [skill for skill in user.skills.all() if skill.category == 'resume_extracted']
            skills_manually_added = [skill for skill in user.skills.all() if skill.category != 'resume_extracted']
            
            return Response({
                'status': 'success',
                'profile_info': {
                    'details': serializer.data,
                    'completion_percentage': calculate_profile_completion(user),
                    'skills_count': user.skills.count(),
                    'has_resume_extracted_skills': len(skills_from_resume) > 0,
                    'has_manually_added_skills': len(skills_manually_added) > 0
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

# Skill management views
@login_required
def manage_skills(request):
    user_skills = request.user.skills.all()
    # Get skills not associated with the user
    available_skills = Skill.objects.exclude(id__in=user_skills.values_list('id', flat=True))
    
    return render(request, 'users/manage_skills.html', {
        'user_skills': user_skills,
        'available_skills': available_skills
    })

@login_required
def add_skill(request):
    if request.method == 'POST':
        skill_id = request.POST.get('skill_id')
        if skill_id:
            skill = get_object_or_404(Skill, id=skill_id)
            if skill not in request.user.skills.all():
                request.user.skills.add(skill)
                messages.success(request, f"Skill '{skill.name}' added to your profile.")
            else:
                messages.info(request, f"Skill '{skill.name}' is already in your profile.")
        return redirect('users:manage_skills')
    return redirect('users:manage_skills')

@login_required
def remove_skill(request, skill_id):
    skill = get_object_or_404(Skill, id=skill_id)
    if skill in request.user.skills.all():
        request.user.skills.remove(skill)
        messages.success(request, f"Skill '{skill.name}' removed from your profile.")
    return redirect('users:manage_skills')

@login_required
def add_custom_skill(request):
    """Add a custom skill manually."""
    
    if request.method == 'POST':
        form = CustomSkillForm(request.POST)
        if form.is_valid():
            # Check if user already has this skill
            skill_name = form.cleaned_data['name']
            
            # Check if skill exists in either direct skills or M2M skills
            user_direct_skills = [s.name.lower() for s in request.user.user_skills_direct.all()]
            user_m2m_skills = [s.name.lower() for s in request.user.skills.all()]
            
            if skill_name.lower() in user_direct_skills or skill_name.lower() in user_m2m_skills:
                messages.warning(request, f"You already have the skill '{skill_name}'")
                return redirect('users:user_skills')
            
            # Check for existing skill with same name but no user
            try:
                existing_skill = Skill.objects.get(name__iexact=skill_name, user__isnull=True)
                # Assign it to this user
                existing_skill.user = request.user
                existing_skill.category = form.cleaned_data['category']
                existing_skill.description = form.cleaned_data['description']
                existing_skill.save()
                
                # Add to M2M if not already there
                if existing_skill not in request.user.skills.all():
                    request.user.skills.add(existing_skill)
                
                messages.success(request, f"Added skill: {skill_name}")
                return redirect('users:user_skills')
            except Skill.DoesNotExist:
                # No existing skill, we'll create a new one
                pass
            except Skill.MultipleObjectsReturned:
                # Multiple skills with the same name but no user
                existing_skill = Skill.objects.filter(name__iexact=skill_name, user__isnull=True).first()
                existing_skill.user = request.user
                existing_skill.category = form.cleaned_data['category']
                existing_skill.description = form.cleaned_data['description']
                existing_skill.save()
                
                # Add to M2M if not already there
                if existing_skill not in request.user.skills.all():
                    request.user.skills.add(existing_skill)
                
                messages.success(request, f"Added skill: {skill_name}")
                return redirect('users:user_skills')
            
            # Create new skill directly associated with the user
            skill = Skill.objects.create(
                name=skill_name,
                category=form.cleaned_data['category'],
                description=form.cleaned_data['description'],
                user=request.user
            )
            
            # Also add to M2M relationship for compatibility
            request.user.skills.add(skill)
            
            messages.success(request, f"Added skill: {skill_name}")
            return redirect('users:user_skills')
    else:
        form = CustomSkillForm()
    
    return render(request, 'users/add_skill.html', {'form': form})

@login_required
def user_skills_view(request):
    """View the current user's skills."""
    # Get direct skills (owned by the user)
    direct_skills = request.user.user_skills_direct.all()
    
    # Get skills from the ManyToMany relationship
    m2m_skills = request.user.skills.all()
    
    # Combine all skills (excluding duplicates)
    all_skill_ids = set(direct_skills.values_list('id', flat=True)) | set(m2m_skills.values_list('id', flat=True))
    all_skills = Skill.objects.filter(id__in=all_skill_ids)
    
    # Group skills by category
    skills_by_category = {}
    for skill in all_skills:
        category = skill.category or "Uncategorized"
        if category not in skills_by_category:
            skills_by_category[category] = []
        skills_by_category[category].append(skill)
    
    context = {
        'direct_skills': direct_skills,
        'm2m_skills': m2m_skills,
        'skills_by_category': skills_by_category
    }
    
    return render(request, 'users/skills.html', context)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_skills_api(request):
    """
    Get all skills for the current user (API endpoint)
    """
    try:
        user = request.user
        # Get all user skills (both direct and M2M)
        direct_skills = user.user_skills_direct.all()
        m2m_skills = user.skills.all()
        
        # Combine all skills (excluding duplicates)
        all_skill_ids = set(direct_skills.values_list('id', flat=True)) | set(m2m_skills.values_list('id', flat=True))
        all_skills = Skill.objects.filter(id__in=all_skill_ids)
        
        # Format skill data for API response
        skill_data = [
            {
                'id': skill.id,
                'name': skill.name,
                'category': skill.category,
                'is_direct': skill in direct_skills,
                'owner': skill.user.username if skill.user else None
            } 
            for skill in all_skills
        ]
        
        return Response({
            'status': 'success',
            'count': len(skill_data),
            'skills': skill_data
        })
    except Exception as e:
        return Response({
            'error': 'Failed to fetch skills',
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
    
    total_hours = CourseProgress.objects.filter(
        user=request.user
    ).aggregate(Sum('estimated_hours_spent'))['estimated_hours_spent__sum'] or 0
    
    streak = LearningStreak.objects.get_or_create(user=request.user)[0]
    
    skills_count = UserSkill.objects.filter(user=request.user).count()
    
    # Get user's skills
    user_skills = UserSkill.objects.filter(user=request.user)
    
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
        'total_hours': total_hours,
        'current_streak': streak.current_streak,
        'skills_count': skills_count,
        'user_skills': user_skills,
        'recent_activity': recent_activity,
        'recent_achievements': recent_achievements,
        'achievements_count': achievements_count,
        'profile_completion': profile_completion,
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