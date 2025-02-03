from django.db import models
from django.conf import settings

class LearningResource(models.Model):
    """
    Model for tracking and redirecting to external learning resources.
    """
    PLATFORM_CHOICES = [
        ('coursera', 'Coursera'),
        ('udemy', 'Udemy'),
        ('linkedin', 'LinkedIn Learning'),
        ('pluralsight', 'PluralSight'),
        ('other', 'Other Platform')
    ]

    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced')
    ]

    # Basic course information
    title = models.CharField(
        max_length=200,
        help_text="Title of the course"
    )
    
    platform = models.CharField(
        max_length=50,
        choices=PLATFORM_CHOICES,
        help_text="Platform hosting the course"
    )
    
    resource_url = models.URLField(
        help_text="Direct link to the course"
    )

    # Course details
    description = models.TextField(
        blank=True,
        help_text="Brief description of what the course covers"
    )
    
    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        help_text="Course difficulty level"
    )

    # Skill relationship
    related_skills = models.ManyToManyField(
        'skills.Skill',
        help_text="Skills this course helps develop"
    )

    # Tracking information
    clicks = models.IntegerField(
        default=0,
        help_text="Number of times this resource was accessed"
    )
    
    last_accessed = models.DateTimeField(
        auto_now=True,
        help_text="Last time this resource was accessed"
    )

    def __str__(self):
        return f"{self.title} ({self.platform})"

    def track_click(self):
        """Increment click counter when resource is accessed"""
        self.clicks += 1
        self.save()