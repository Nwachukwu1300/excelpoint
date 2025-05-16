from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication endpoints
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    
    # Profile endpoints
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Skill management endpoints
    path('skills/', views.user_skills_view, name='user_skills'),
    path('skills/add/', views.add_skill, name='add_skill'),
    path('skills/remove/<int:skill_id>/', views.remove_skill, name='remove_skill'),
    path('skills/add-custom/', views.add_custom_skill, name='add_custom_skill'),
    
    # Achievement management endpoints
    path('achievements/', views.manage_achievements, name='manage_achievements'),
    path('achievements/edit/<int:achievement_id>/', views.edit_achievement, name='edit_achievement'),
    path('achievements/delete/<int:achievement_id>/', views.delete_achievement, name='delete_achievement'),
    
    # Certification management endpoints
    path('certifications/', views.manage_certifications, name='manage_certifications'),
    path('certifications/edit/<int:certification_id>/', views.edit_certification, name='edit_certification'),
    path('certifications/delete/<int:certification_id>/', views.delete_certification, name='delete_certification'),
]