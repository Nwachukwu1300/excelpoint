from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import UserSerializer
from django.contrib.auth import login, logout, authenticate

# Registration View
@api_view(['POST'])  # Only allow POST requests for registration
@permission_classes([AllowAny])  # Anyone can register
def register_user(request):
    """
    Handles new user registration with profile information.
    
    Parameters:
        request.data (dict): Contains user registration data including:
            - username
            - email
            - password
            - current_role (optional)
            - experience_level (optional)
            - bio (optional)
    
    Returns:
        Response: User creation status and ID if successful
    """
    try:
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': 'User registered successfully',
                'user_id': user.id,
                'username': user.username  # Added for confirmation
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        # Handle unexpected errors gracefully
        return Response({
            'error': 'Registration failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# Login View
@api_view(['POST'])  # Added missing decorator
@permission_classes([AllowAny])  # Added missing decorator
def login_user(request):
    """
    Authenticates user and creates session.
    
    Parameters:
        request.data (dict):
            - username: User's username
            - password: User's password
    
    Returns:
        Response: User profile and career information if login successful
    """
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        
        # Input validation with specific messages
        if not username:
            return Response({
                'error': 'Username is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        if not password:
            return Response({
                'error': 'Password is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Structured user data response
            return Response({
                'status': 'success',
                'message': 'Login successful',
                'user_info': {
                    'id': user.id,
                    'username': user.username,
                    'current_role': user.current_role,
                    'experience_level': user.experience_level,
                    'bio': user.bio,
                },
                'profile_completion': calculate_profile_completion(user)
            })
        
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
        
    except Exception as e:
        # Handle unexpected errors
        return Response({
            'error': 'Login failed',
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
@permission_classes([IsAuthenticated])  # Only logged-in users can logout
def logout_user(request):
    """
    Handles user logout by ending their session.
    
    Parameters:
        request: Request object with user session
        
    Returns:
        Response: Logout confirmation message
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
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    Retrieves the full profile of the currently logged-in user.
    """
    try:
        serializer = UserSerializer(request.user)
        return Response({
            'status': 'success',
            'profile': serializer.data
        })
    except Exception as e:
        return Response({
            'error': 'Failed to fetch profile',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Updates the profile of the currently logged-in user.
    """
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