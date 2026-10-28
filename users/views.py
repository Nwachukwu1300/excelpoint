from django.shortcuts import redirect
from django.contrib.auth import login
from django.contrib import messages
from django.utils.crypto import constant_time_compare
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

