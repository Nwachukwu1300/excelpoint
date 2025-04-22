from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from skills.models import Course, Skill

User = get_user_model()

class CourseProgress(models.Model):
    STATUS_CHOICES = (
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('paused', 'Paused')
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_progress')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='user_progress')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    progress_percent = models.IntegerField(default=0, help_text="Percentage complete (0-100)")
    date_started = models.DateTimeField(null=True, blank=True)
    date_completed = models.DateTimeField(null=True, blank=True)
    last_activity_date = models.DateTimeField(auto_now=True)
    estimated_hours_spent = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    notes = models.TextField(blank=True, help_text="User notes about this course")
    
    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-last_activity_date']
    
    def save(self, *args, **kwargs):
        # Set date_started when status changes to in_progress
        if self.status == 'in_progress' and not self.date_started:
            self.date_started = timezone.now()
        
        # Set date_completed when status changes to completed
        if self.status == 'completed' and not self.date_completed:
            self.date_completed = timezone.now()
            self.progress_percent = 100
        
        super().save(*args, **kwargs)
        
        # Update user skills when a course is completed
        if self.status == 'completed':
            self.update_user_skills()
    
    def update_user_skills(self):
        """Update user skills when a course is completed"""
        from skills.models import UserSkill
        
        # Get all skills associated with this course
        course_skills = self.course.courseskill_set.all()
        
        for course_skill in course_skills:
            # Check if user already has this skill
            user_skill, created = UserSkill.objects.get_or_create(
                user=self.user,
                skill_name=course_skill.skill_name,
                defaults={
                    'proficiency_level': course_skill.proficiency_level,
                    'is_verified': False
                }
            )
            
            # If not created, update the proficiency level if course offers higher level
            if not created:
                proficiency_map = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
                
                current_level = proficiency_map.get(user_skill.proficiency_level, 1)
                course_level = proficiency_map.get(course_skill.proficiency_level, 1)
                
                if course_level > current_level:
                    user_skill.proficiency_level = course_skill.proficiency_level
                    user_skill.save()

class LearningStreak(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='learning_streak')
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    
    def update_streak(self):
        today = timezone.now().date()
        
        if not self.last_activity_date:
            # First activity
            self.current_streak = 1
            self.longest_streak = 1
        elif self.last_activity_date == today:
            # Already logged activity today
            pass
        elif self.last_activity_date == today - timezone.timedelta(days=1):
            # Consecutive day
            self.current_streak += 1
            self.longest_streak = max(self.current_streak, self.longest_streak)
        else:
            # Streak broken
            self.current_streak = 1
        
        self.last_activity_date = today
        self.save()

class Achievement(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, help_text="Font Awesome icon class")
    requirement_type = models.CharField(max_length=50, help_text="Type of achievement (courses_completed, streak, etc.)")
    requirement_value = models.IntegerField(help_text="Value required to earn this achievement")
    
    def __str__(self):
        return self.name

class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    date_earned = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'achievement')

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