from django.db import models

class Skill(models.Model):
    """
    Model to represent professional skills.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
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
    
    def __str__(self):
        return self.name