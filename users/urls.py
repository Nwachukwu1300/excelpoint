from django.urls import path, re_path
from django.views.generic import RedirectView
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication endpoints
    # Sign-in and registration are in the React app; ?next= is passed along
    path('register/', RedirectView.as_view(url='/app/register', query_string=True), name='register'),
    path('login/', RedirectView.as_view(url='/app/login', query_string=True), name='login'),
    
    # Google OAuth endpoints
    path('google/login/', views.google_oauth_initiate, name='google_login'),
    path('google/callback/', views.google_oauth_callback, name='google_callback'),
    
    path('change-password/', RedirectView.as_view(url='/app/settings/password'), name='change_password'),  # now in the app
    path('settings/', RedirectView.as_view(url='/app/settings'), name='settings'),

    # Notifications
    path('notifications/', RedirectView.as_view(url='/app/notifications'), name='notifications'),

    # The old logout page and career pages (profile, achievements, certifications, education) were removed
    re_path(r'^(logout|profile|achievements|certifications|education)(/.*)?$', RedirectView.as_view(url='/app/')),
]
