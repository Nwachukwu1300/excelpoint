"""Learning management models for the Excelpoint application.

This module provides data structures for tracking user learning progress,
course management, and external resource integration. It enables users
to track their educational journey across various platforms and maintain
progress notes for continuous improvement.

Key features:
- Course tracking with progress monitoring
- External learning resource management
- Progress notes and activity history
- Learning path recommendations
- Time tracking and completion metrics
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

# Import Course model from learning app itself
class Course(models.Model):
    """Model for courses in the learning platform.
    
    This model represents external courses that users can track and
    progress through. It stores metadata about courses including
    difficulty levels, duration, and external URLs for access.
    """
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructor = models.CharField(max_length=100)
    duration_hours = models.IntegerField(default=0)
    difficulty_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced')
        ],
        default='beginner'
    )
    course_url = models.URLField(
        blank=True,
        null=True,
        help_text="External link to the course (e.g., Coursera, Udemy, etc.)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_free = models.BooleanField(default=True, help_text="Is this course free?")
    
    def __str__(self):
        return self.title

class CourseProgressNote(models.Model):
    """Model to store the history of notes and updates for course progress.
    
    This model maintains a chronological record of user notes, insights,
    and progress updates for each course. It enables users to track their
    learning journey and maintain context across learning sessions.
    """
    progress = models.ForeignKey('CourseProgress', on_delete=models.CASCADE, related_name='notes_history')
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Note for {self.progress.course.title} - {self.created_at.strftime('%Y-%m-%d')}"

class CourseProgress(models.Model):
    """Tracks user progress through individual courses.
    
    This model maintains the state of a user's progress through a specific
    course, including status tracking, time estimates, and activity dates.
    It automatically manages start and completion dates based on status changes.
    """
    STATUS_CHOICES = (
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('paused', 'Paused')
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_progress')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='user_progress')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    date_started = models.DateTimeField(null=True, blank=True)
    date_completed = models.DateTimeField(null=True, blank=True)
    last_activity_date = models.DateTimeField(auto_now=True)
    estimated_hours_spent = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    
    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-last_activity_date']
    
    def save(self, *args, **kwargs):
        """Override save to automatically manage start and completion dates.
        
        Automatically sets date_started when status changes to 'in_progress'
        and date_completed when status changes to 'completed'.
        """
        # Set date_started when status changes to in_progress
        if self.status == 'in_progress' and not self.date_started:
            self.date_started = timezone.now()
        
        # Set date_completed when status changes to completed
        if self.status == 'completed' and not self.date_completed:
            self.date_completed = timezone.now()
        
        super().save(*args, **kwargs)

class LearningResource(models.Model):
    """Model for tracking and redirecting to external learning resources.
    
    This model provides a curated collection of external learning materials
    across various platforms. It enables users to discover new resources
    and track their usage patterns for personalized recommendations.
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

class SavedResource(models.Model):
    """
    Model for storing user's saved learning resources.
    """
    RESOURCE_TYPE_CHOICES = [
        ('article', 'Article'),
        ('video', 'Video'),
        ('book', 'Book'),
        ('podcast', 'Podcast'),
        ('documentation', 'Documentation'),
        ('other', 'Other')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_resources')
    title = models.CharField(max_length=200)
    url = models.URLField()
    description = models.TextField(blank=True)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES)
    date_saved = models.DateTimeField(auto_now_add=True)
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    notes = models.TextField(blank=True, help_text="Personal notes about this resource")
    
    class Meta:
        ordering = ['-date_saved']
        indexes = [
            models.Index(fields=['user', 'resource_type']),
            models.Index(fields=['date_saved'])
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_resource_type_display()})"
    
    def get_tags_list(self):
        """Return list of tags"""
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

class Achievement(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, help_text='Emoji or icon class')
    requirement_type = models.CharField(
        max_length=50,
        help_text='Type of achievement (courses_completed, streak, skill_level, total_hours)'
    )
    requirement_value = models.IntegerField(
        help_text='Value required to earn this achievement'
    )
    
    def __str__(self):
        return self.name

class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    date_earned = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'achievement')
    
    def __str__(self):
        return f"{self.user.username} earned {self.achievement.name}"