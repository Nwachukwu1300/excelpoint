# Google OAuth Setup Guide for ExcelPoint

This guide will help you set up Google OAuth authentication for your ExcelPoint project.

## Prerequisites

1. A Google account
2. Access to Google Cloud Console
3. Your Career Nexus project running locally

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API (if not already enabled)

## Step 2: Configure OAuth Consent Screen

1. In Google Cloud Console, go to **APIs & Services** > **OAuth consent screen**
2. Choose **External** user type (unless you have a Google Workspace)
3. Fill in the required information:
   - **App name**: ExcelPoint
   - **User support email**: Your email
   - **Developer contact information**: Your email
4. Add the following scopes:
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/userinfo.profile`
5. Add test users (your email) if in testing mode
6. Save and continue

## Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth 2.0 Client IDs**
3. Choose **Web application**
4. Set the following:
   - **Name**: Career Nexus Web Client
   - **Authorized JavaScript origins**:
     - `http://localhost:8000` (for development)
     - `https://yourdomain.com` (for production)
   - **Authorized redirect URIs**:
     - `http://localhost:8000/users/google/callback/` (for development)
     - `https://yourdomain.com/users/google/callback/` (for production)
5. Click **Create**
6. Copy the **Client ID** and **Client Secret**

## Step 4: Configure Environment Variables

Create a `.env` file in your project root with the following variables:

```bash
# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID=your-client-id-here
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret-here
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/users/google/callback/
```

## Step 5: Install Dependencies

Install the required Python packages:

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2
```

Or update your requirements.txt and run:

```bash
pip install -r requirements.txt
```

## Step 6: Test the Integration

1. Start your Django development server:
   ```bash
   python manage.py runserver
   ```

2. Navigate to `http://localhost:8000/users/register/`
3. Click the "Continue with Google" button
4. Complete the OAuth flow
5. Verify that you're redirected back to your application and logged in

## Troubleshooting

### Common Issues

1. **"redirect_uri_mismatch" error**
   - Ensure the redirect URI in your Google Cloud Console exactly matches your environment variable
   - Check for trailing slashes and protocol (http vs https)

2. **"invalid_client" error**
   - Verify your Client ID and Client Secret are correct
   - Ensure you're using the correct credentials for your environment

3. **"access_denied" error**
   - Check that your OAuth consent screen is properly configured
   - Ensure you've added your email as a test user if in testing mode

4. **"invalid_grant" error**
   - This usually occurs when the authorization code has expired
   - Try the OAuth flow again

### Debug Mode

To enable debug logging for OAuth, add this to your Django settings:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'users.services': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## Production Deployment

For production deployment:

1. Update your Google Cloud Console credentials with production URLs
2. Set `DEBUG=False` in your Django settings
3. Use HTTPS in production
4. Update the redirect URI to your production domain
5. Consider using environment-specific settings files

## Security Considerations

1. **Never commit your Client Secret to version control**
2. **Use environment variables for sensitive data**
3. **Enable HTTPS in production**
4. **Regularly rotate your OAuth credentials**
5. **Monitor OAuth usage in Google Cloud Console**

## Additional Features

### Custom User Fields

The Google OAuth integration automatically populates:
- Email address
- First name
- Last name
- Username (generated from email)

You can extend the `create_or_update_user` method in `users/services.py` to handle additional fields like:
- Profile picture
- Google ID for linking accounts
- Additional profile information

### Account Linking

To allow users to link their Google account to an existing email-based account, you can modify the `create_or_update_user` method to check for existing users by email and prompt for account linking.

## Support

If you encounter issues:

1. Check the Django logs for error messages
2. Verify your Google Cloud Console configuration
3. Test with a fresh browser session
4. Ensure all environment variables are properly set 