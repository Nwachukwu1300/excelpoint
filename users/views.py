from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import UserSerializer
from django.contrib.auth import login, logout, authenticate


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
            return Response({
                'status': 'success',
                'profile_info': {
                    'details': serializer.data,
                    'completion_percentage': calculate_profile_completion(user)
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