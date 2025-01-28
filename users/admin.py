from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    """
    Custom admin interface for User model.
    """
    list_display = ('username', 'email', 'current_role', 'experience_level')
    list_filter = ('experience_level', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Career Information', {
            'fields': ('current_role', 'experience_level', 'bio', 
                      'linkedin_profile', 'github_profile')
        }),
    )

admin.site.register(User, CustomUserAdmin)