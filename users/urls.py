from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication endpoints
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    
    # Google OAuth endpoints
    path('google/login/', views.google_oauth_initiate, name='google_login'),
    path('google/callback/', views.google_oauth_callback, name='google_callback'),
    
    # Profile endpoints
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('settings/', views.settings_view, name='settings'),
    
    # Achievement management endpoints
    path('achievements/', views.manage_achievements, name='manage_achievements'),
    path('achievements/edit/<int:achievement_id>/', views.edit_achievement, name='edit_achievement'),
    path('achievements/delete/<int:achievement_id>/', views.delete_achievement, name='delete_achievement'),
    
    # Certification management endpoints
    path('certifications/', views.manage_certifications, name='manage_certifications'),
    path('certifications/edit/<int:certification_id>/', views.edit_certification, name='edit_certification'),
    path('certifications/delete/<int:certification_id>/', views.delete_certification, name='delete_certification'),
    
    # Education management endpoints
    path('education/', views.manage_education, name='manage_education'),
    path('education/edit/<int:education_id>/', views.edit_education, name='edit_education'),
    path('education/delete/<int:education_id>/', views.delete_education, name='delete_education'),
]