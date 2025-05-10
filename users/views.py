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
from .forms import RegistrationForm, UserProfileForm, CustomSkillForm
from skills.models import Skill
from .models import User
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from learning.models import CourseProgress, LearningStreak, UserAchievement
from skills.models import UserSkill


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def register_user(request):
   """
   Registration endpoint.
   GET: Shows template
   POST: Creates new user
   """
   if request.method == 'GET':
       default_content = {
           "username": "gbemi",
           "email": "gbemi@example.com", 
           "password": "test123.",
           "password2": "test123.",
           
           "current_role": "Software Developer",
           "experience_level": "senior" 
       }
       return Response(default_content)

   if request.method == 'POST':
       serializer = UserSerializer(data=request.data)
       if serializer.is_valid():
           user = serializer.save()
           return Response({
               'message': 'User registered successfully',
               'user_id': user.id,
               'username': user.username
           }, status=status.HTTP_201_CREATED)
       
       return Response({
           'status': 'error', 
           'errors': serializer.errors
       }, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def login_user(request):
    """
    Handles login and logout functionality.
    """
    if request.method == 'GET':
        # Show different templates based on authentication status
        if request.user.is_authenticated:
            default_content = {
                "action": "logout"
            }
        else:
            default_content = {
                "username": "enter_username",
                "password": "enter_password"
            }
        return Response(default_content)

    if request.method == 'POST':
        try:
            # Check if this is a logout request
            action = request.data.get('action')
            
            if action == 'logout':
                if request.user.is_authenticated:
                    logout(request)
                    return Response({
                        'status': 'success',
                        'message': 'Successfully logged out'
                    })
                else:
                    return Response({
                        'error': 'Not logged in'
                    }, status=status.HTTP_401_UNAUTHORIZED)

            # Handle login
            username = request.data.get('username')
            password = request.data.get('password')
            
            if not username or not password:
                return Response({
                    'error': 'Both username and password are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                return Response({
                    'status': 'success',
                    'message': 'Login successful',
                    'user_info': {
                        'id': user.id,
                        'username': user.username,
                        'current_role': user.current_role,
                        'experience_level': user.experience_level,
                    }
                })
            
            return Response({
                'error': 'Invalid credentials you many not have an account yet'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        except Exception as e:
            return Response({
                'error': 'Operation failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """
    Handles logout - requires active session
    """
    try:
        logout(request)
        return Response({
            'status': 'success',
            'message': 'Successfully logged out'
        })
    except Exception as e:
        return Response({
            'error': 'Logout failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




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
    earned_achievements = UserAchievement.objects.filter(
        user=request.user
    ).select_related('achievement')
    
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
    
    # Get recent achievements
    recent_achievements = earned_achievements.order_by('-date_earned')[:3]
    achievements_count = earned_achievements.count()
    
    return render(request, 'users/profile.html', {
        'completed_courses': completed_courses,
        'total_hours': total_hours,
        'current_streak': streak.current_streak,
        'skills_count': skills_count,
        'user_skills': user_skills,
        'recent_activity': recent_activity,
        'recent_achievements': recent_achievements,
        'achievements_count': achievements_count
    })

@login_required
def edit_profile(request):
    """Edit user profile information"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            # Update user model fields
            user = request.user
            user.first_name = form.cleaned_data.get('first_name', user.first_name)
            user.last_name = form.cleaned_data.get('last_name', user.last_name)
            user.email = form.cleaned_data.get('email', user.email)
            user.current_role = form.cleaned_data.get('current_role', user.current_role)
            user.experience_level = form.cleaned_data.get('experience_level', user.experience_level)
            user.save()
            
            # Update profile model
            form.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('users:profile')
    else:
        # Initialize form with current user data
        initial_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'current_role': request.user.current_role,
            'experience_level': request.user.experience_level,
        }
        form = UserProfileForm(instance=request.user.profile, initial=initial_data)
    
    return render(request, 'users/edit_profile.html', {
        'form': form,
        'user': request.user
    })