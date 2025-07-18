import os
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db import transaction
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

# Optional Google OAuth imports - only import if credentials are configured
try:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    from google_auth_oauthlib.flow import Flow
    from google.auth.exceptions import GoogleAuthError
    GOOGLE_OAUTH_AVAILABLE = True
except ImportError:
    GOOGLE_OAUTH_AVAILABLE = False
    logger.warning("Google OAuth libraries not available. Google OAuth will be disabled.")


class GoogleOAuthService:
    """
    Service class to handle Google OAuth authentication.
    """
    
    def __init__(self):
        if not GOOGLE_OAUTH_AVAILABLE:
            raise ImportError("Google OAuth libraries not available. Please install google-auth, google-auth-oauthlib, and google-auth-httplib2")
        
        self.client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', None)
        self.client_secret = getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', None)
        self.redirect_uri = getattr(settings, 'GOOGLE_OAUTH_REDIRECT_URI', None)
        self.scopes = getattr(settings, 'GOOGLE_OAUTH_SCOPES', ['openid', 'email', 'profile'])
        
        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("Google OAuth credentials not properly configured. Please set GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, and GOOGLE_OAUTH_REDIRECT_URI in your settings.")
    
    def get_authorization_url(self):
        """
        Generate the authorization URL for Google OAuth.
        """
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                    "scopes": self.scopes
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        # Disable scope checking for authorization URL generation
        flow._OAuth2Flow__scope_check_disabled = True
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return authorization_url
    
    def exchange_code_for_token(self, authorization_code):
        """
        Exchange authorization code for access token.
        """
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                    "scopes": self.scopes
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        try:
            # Completely disable scope checking
            flow._OAuth2Flow__scope_check_disabled = True
            
            # Exchange code for token
            flow.fetch_token(code=authorization_code)
            return flow.credentials
        except Exception as e:
            logger.error(f"Error exchanging code for token: {str(e)}")
            raise
    
    def get_user_info(self, credentials):
        """
        Get user information from Google using the access token.
        """
        try:
            # First try to get info from ID token (OpenID Connect)
            if hasattr(credentials, 'id_token') and credentials.id_token:
                id_info = id_token.verify_oauth2_token(
                    credentials.id_token, 
                    google_requests.Request(), 
                    self.client_id
                )
                return id_info
            
            # Fallback: get user info from userinfo endpoint
            headers = {
                'Authorization': f'Bearer {credentials.token}',
                'Content-Type': 'application/json',
            }
            
            response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers=headers
            )
            
            if response.status_code == 200:
                user_info = response.json()
                # Add sub field for consistency with ID token
                if 'id' in user_info and 'sub' not in user_info:
                    user_info['sub'] = user_info['id']
                return user_info
            else:
                logger.error(f"Failed to get user info: {response.status_code} - {response.text}")
                raise Exception(f"Failed to get user info: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            raise
    
    def authenticate_or_create_user(self, user_info):
        """
        Authenticate existing user or create new user from Google info.
        """
        email = user_info.get('email')
        google_id = user_info.get('sub')
        
        if not email:
            raise ValueError("Email is required from Google OAuth")
        
        try:
            with transaction.atomic():
                # Try to find existing user by email
                user = User.objects.filter(email=email).first()
                
                if user:
                    # Update user's Google ID if not set
                    if not hasattr(user, 'google_id') or not user.google_id:
                        user.google_id = google_id
                        user.save(update_fields=['google_id'])
                    return user
                
                # Create new user
                username = self._generate_unique_username(user_info.get('given_name', ''), user_info.get('family_name', ''))
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=user_info.get('given_name', ''),
                    last_name=user_info.get('family_name', ''),
                    google_id=google_id
                )
                
                # Create user profile
                if hasattr(user, 'profile'):
                    user.profile.save()
                
                logger.info(f"Created new user via Google OAuth: {user.username}")
                return user
                
        except Exception as e:
            logger.error(f"Error creating/authenticating user: {e}")
            raise
    
    def _generate_unique_username(self, first_name, last_name):
        """
        Generate a unique username from Google user info.
        """
        base_username = f"{first_name.lower()}{last_name.lower()}".replace(' ', '')
        username = base_username
        counter = 1
        
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        return username


class GoogleOAuthBackend:
    """
    Custom authentication backend for Google OAuth users.
    """
    
    def authenticate(self, request, google_id=None, email=None):
        if not google_id and not email:
            return None
        
        try:
            if google_id:
                user = User.objects.filter(google_id=google_id).first()
            else:
                user = User.objects.filter(email=email).first()
            
            return user
        except Exception as e:
            logger.error(f"Error in Google OAuth authentication: {e}")
            return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None 