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

    # OAuth fields
    google_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text="Google OAuth user ID"
    )

    # Career-specific fields
    current_role = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="User's current job position"
    )

    dream_role = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="User's desired career goal"
    )

    experience_level = models.CharField(
        max_length=20, 
        choices=EXPERIENCE_LEVELS,
        default='entry',
        help_text="User's current experience level"
    )

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

class UserEducation(models.Model):
    """
    Model for storing a user's educational background.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='education'
    )
    
    institution = models.CharField(
        max_length=200,
        help_text="School, college, or university name"
    )
    
    degree = models.CharField(
        max_length=200,
        help_text="Degree or certificate earned"
    )
    
    field_of_study = models.CharField(
        max_length=200,
        blank=True,
        help_text="Major or field of study"
    )
    
    graduation_date = models.CharField(
        max_length=50,
        blank=True,
        help_text="Date or year of graduation"
    )
    
    gpa = models.CharField(
        max_length=10,
        blank=True,
        help_text="GPA or academic performance metric"
    )
    
    additional_info = models.TextField(
        blank=True,
        help_text="Additional information, honors, activities, etc."
    )
    
    date_added = models.DateTimeField(
        auto_now_add=True
    )
    
    class Meta:
        ordering = ['-graduation_date', 'institution']
        verbose_name_plural = "User education"
    
    def __str__(self):
        return f"{self.degree} from {self.institution}"

class UserCertification(models.Model):
    """
    Model for storing a user's professional certifications.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='certifications'
    )
    
    name = models.CharField(
        max_length=200,
        help_text="Certification name or title"
    )
    
    issuer = models.CharField(
        max_length=200,
        blank=True,
        help_text="Organization that issued the certification"
    )
    
    date_earned = models.CharField(
        max_length=50,
        blank=True,
        help_text="Date when the certification was earned"
    )
    
    expiration_date = models.CharField(
        max_length=50,
        blank=True,
        help_text="Expiration date (if applicable)"
    )
    
    credential_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Certification number or credential ID"
    )
    
    credential_url = models.URLField(
        blank=True,
        help_text="URL to verify the certification"
    )
    
    date_added = models.DateTimeField(
        auto_now_add=True
    )
    
    class Meta:
        ordering = ['-date_earned', 'name']
        verbose_name_plural = "User certifications"
    
    def __str__(self):
        return f"{self.name} ({self.issuer})" if self.issuer else self.name

class UserAchievement(models.Model):
    """
    Model for storing a user's professional achievements, awards, and honors.
    Different from learning achievements which are tracked in the learning app.
    """
    ACHIEVEMENT_TYPES = [
        ('award', 'Award'),
        ('scholarship', 'Scholarship'),
        ('honor', 'Honor/Recognition'),
        ('publication', 'Publication'),
        ('patent', 'Patent'),
        ('grant', 'Grant'),
        ('general', 'General Achievement')
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_achievements'
    )
    
    title = models.CharField(
        max_length=200,
        help_text="Achievement title"
    )
    
    type = models.CharField(
        max_length=20,
        choices=ACHIEVEMENT_TYPES,
        default='general',
        help_text="Type of achievement"
    )
    
    organization = models.CharField(
        max_length=200,
        blank=True,
        help_text="Organization that granted the achievement"
    )
    
    date_received = models.CharField(
        max_length=50,
        blank=True,
        help_text="Date when the achievement was received"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Description of the achievement and its significance"
    )
    
    date_added = models.DateTimeField(
        auto_now_add=True
    )
    
    class Meta:
        ordering = ['-date_received', 'title']
        verbose_name_plural = "User achievements"
    
    def __str__(self):
        return f"{self.title} ({self.get_type_display()})"