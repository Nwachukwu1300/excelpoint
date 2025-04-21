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

class CareerRole(models.Model):
    """
    Model to represent career roles/paths that users can aspire to.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the career role"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Description of the role and responsibilities"
    )
    
    category = models.CharField(
        max_length=50,
        blank=True,
        help_text="Category of role (e.g., Development, Data Science, Design)"
    )
    
    def __str__(self):
        return self.name

class RoleSkill(models.Model):
    """
    Model to map required skills to career roles.
    """
    role = models.ForeignKey(
        CareerRole, 
        on_delete=models.CASCADE,
        related_name='required_skills',
        help_text="The career role"
    )
    
    skill_name = models.CharField(
        max_length=100,
        help_text="Name of the required skill"
    )
    
    importance = models.CharField(
        max_length=20,
        choices=[
            ('essential', 'Essential'),
            ('important', 'Important'),
            ('nice_to_have', 'Nice to Have')
        ],
        default='important',
        help_text="Importance level of this skill for the role"
    )
    
    class Meta:
        unique_together = ('role', 'skill_name')
        
    def __str__(self):
        return f"{self.skill_name} for {self.role.name}"

class Course(models.Model):
    """
    Model to represent learning courses/resources.
    """
    title = models.CharField(
        max_length=200,
        help_text="Title of the course"
    )
    
    provider = models.CharField(
        max_length=100,
        help_text="Provider or platform offering the course"
    )
    
    url = models.URLField(
        help_text="Link to the course"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Description of the course"
    )
    
    difficulty = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced')
        ],
        default='intermediate',
        help_text="Difficulty level of the course"
    )
    
    duration = models.CharField(
        max_length=50,
        blank=True,
        help_text="Estimated duration to complete (e.g., '4 weeks', '10 hours')"
    )
    
    is_free = models.BooleanField(
        default=False,
        help_text="Whether the course is free"
    )
    
    skills_taught = models.ManyToManyField(
        'skills.Skill',
        related_name='courses',
        blank=True,
        help_text="Skills taught by this course"
    )
    
    def __str__(self):
        return self.title

class CourseSkill(models.Model):
    """
    Model to map skills to courses.
    """
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        help_text="The course teaching this skill"
    )
    
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Reference to the skill being taught"
    )
    
    skill_name = models.CharField(
        max_length=100,
        help_text="Name of the skill taught"
    )
    
    proficiency_level = models.CharField(
        max_length=20,
        choices=[
            ('basic', 'Basic'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced')
        ],
        default='intermediate',
        help_text="Level of proficiency taught for this skill"
    )
    
    class Meta:
        unique_together = ('course', 'skill_name')
        
    def __str__(self):
        return f"{self.skill_name} in {self.course.title}"