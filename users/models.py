"""User management models for the Excelpoint application.

This module extends Django's built-in user system with career-focused
features including OAuth integration, profile management, and education
tracking. It provides a foundation for personalized learning experiences
and career development tracking.

Key features:
- Extended User model with career-specific fields
- OAuth integration via Google
- Profile management with avatar support
- Education and experience tracking
- File storage abstraction for profile assets
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models #gives us access to Django's database field types (like CharField, URLField, etc.).
from django.conf import settings

class FileStorageMixin:
    """Mixin providing file storage abstraction across storage backends.
    
    This mixin allows models to work with both local filesystem and S3
    storage without changing their implementation. It delegates storage
    operations to the appropriate service based on Django settings.
    """
    
    def save_file(self, file_obj, path):
        """Save a file using the currently configured storage backend.
        
        Args:
            file_obj: File object to save
            path: Destination path within the storage
        """
        from subjects.services.storage_factory import StorageFactory
        storage_service = StorageFactory.get_storage_service()
        return storage_service.save_file(file_obj, path)
    
    def get_file_url(self, path):
        """Get the public URL for a stored file.
        
        Args:
            path: Path to the file in storage
        Returns:
            Public URL for accessing the file
        """
        from subjects.services.storage_factory import StorageFactory
        storage_service = StorageFactory.get_storage_service()
        return storage_service.get_file_url(path)
    
    def delete_file(self, path):
        """Delete a file from the configured storage backend.
        
        Args:
            path: Path to the file to delete
        """
        from subjects.services.storage_factory import StorageFactory
        storage_service = StorageFactory.get_storage_service()
        storage_service.delete_file(path)

class User(AbstractUser):
    """Extended user model with career-focused features.
    
    This model extends Django's AbstractUser with additional fields
    for career development, OAuth integration, and personalized
    learning experiences. It serves as the central identity for
    all user interactions within the application.
    
    Key additions:
    - Google OAuth integration
    - Career role and experience tracking
    - Professional profile links
    - Bio and background information
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

def get_storage_backend():
    """Get the appropriate storage backend based on Django settings.
    
    Returns:
        Storage backend instance (S3Boto3Storage or FileSystemStorage)
    """
    if getattr(settings, 'STORAGE_BACKEND', 'local') == 's3':
        from storages.backends.s3boto3 import S3Boto3Storage
        return S3Boto3Storage()
    else:
        from django.core.files.storage import FileSystemStorage
        return FileSystemStorage()

class UserProfile(models.Model):
    """Extended user profile for additional personal information.
    
    This model stores supplementary user data that doesn't fit in the
    core User model, such as avatars, detailed education history,
    and extended career information. It maintains a one-to-one
    relationship with the User model.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    avatar = models.ImageField(
        upload_to='avatars/',
        storage=get_storage_backend(),
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
    
    EDUCATION_LEVEL_CHOICES = [
        ('high_school', 'High school'),
        ('undergraduate', 'Undergraduate'),
        ('postgraduate', 'Postgraduate'),
        ('working_professional', 'Working professional'),
        ('other', 'Other'),
    ]
    education_level = models.CharField(
        max_length=32,
        choices=EDUCATION_LEVEL_CHOICES,
        null=True,
        blank=True,
        help_text="Highest level of education (nullable)"
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