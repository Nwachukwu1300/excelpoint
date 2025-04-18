from django.db import models
from django.conf import settings

class Skill(models.Model):
    """
    Model to represent professional skills.
    """
    name = models.CharField(
        max_length=100,
        help_text="Name of the skill"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Description of the skill"
    )
    
    category = models.CharField(
        max_length=50,
        blank=True,
        help_text="Category of skill (e.g., Technical, Soft Skills, etc.)"
    )
    
    # Add direct relationship to user
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_skills_direct',
        null=True,
        blank=True,
        help_text="User who owns this skill"
    )
    
    class Meta:
        # Only one skill with a specific name per user
        # But different users can have skills with the same name
        unique_together = ('name', 'user')
    
    def __str__(self):
        return self.name