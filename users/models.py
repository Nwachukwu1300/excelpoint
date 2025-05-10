from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models #gives us access to Django's database field types (like CharField, URLField, etc.).

class User(AbstractUser):
    """
    Extended user model.
    Stores additional career-related information about users.
    """
    EXPERIENCE_LEVELS = [
        ('entry', 'Entry Level'),
        ('mid', 'Mid Level'),
        ('senior', 'Senior Level'),
    ]

    # Career-specific fields
    current_role = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="User's current job position"
    )

    experience_level = models.CharField(
        max_length=20, 
        choices=EXPERIENCE_LEVELS,
        default='entry',
        help_text="User's current experience level"
    )

    dream_job = models.ForeignKey(
        'skills.CareerRole',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='aspiring_users',
        help_text="User's target career role"
    )

    skills = models.ManyToManyField(
        'skills.Skill', 
        blank=True,
        related_name='user_skills',
        help_text="Skills associated with the user")
    
    bio = models.TextField(
        blank=True,
        help_text="Professional summary and background")
    linkedin_profile = models.URLField(blank=True)
    github_profile = models.URLField(blank=True)

    def __str__(self):
        return self.username

class UserProfile(models.Model):
    """
    User profile model for storing additional user information.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        help_text="User's profile picture"
    )
    
    bio = models.TextField(
        blank=True,
        help_text="Professional summary and background"
    )
    
    linkedin_profile = models.URLField(
        blank=True,
        help_text="LinkedIn profile URL"
    )
    
    github_profile = models.URLField(
        blank=True,
        help_text="GitHub profile URL"
    )
    
    def __str__(self):
        return f"{self.user.username}'s profile"