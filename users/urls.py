from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication endpoints
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    
    # Profile endpoints
    path('profile/', views.user_profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Skill management endpoints
    path('skills/', views.manage_skills, name='manage_skills'),
    path('skills/add/', views.add_skill, name='add_skill'),
    path('skills/remove/<int:skill_id>/', views.remove_skill, name='remove_skill'),
    path('skills/add-custom/', views.add_custom_skill, name='add_custom_skill'),
    
    # User skills routes
    path('skills/', views.user_skills_view, name='user_skills'),
    path('api/skills/', views.user_skills_api, name='user_skills_api'),
]