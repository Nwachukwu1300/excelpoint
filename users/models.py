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