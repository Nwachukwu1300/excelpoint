"""User models: the custom User (with Google sign-in), a small profile, and in-app notifications."""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class User(AbstractUser):
    """The app's user: Django's user plus a Google OAuth id."""

    google_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text="Google OAuth user ID"
    )

    def __str__(self):
        return self.username


# Kept because users migration 0006 references it (the avatar field it served is gone)
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
    """Per-user settings beyond the User model; created for every user by users.signals."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
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


class Notification(models.Model):
    """In-app notification: workflow results, review reminders, suggestions."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    kind = models.CharField(max_length=30)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    url = models.CharField(max_length=500, blank=True, help_text="Site-relative link, e.g. /subjects/3/")
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'read_at'])]

    def __str__(self):
        return f"{self.kind}: {self.title}"

    @classmethod
    def notify(cls, user, kind, title, body='', url=''):
        return cls.objects.create(user=user, kind=kind, title=title, body=body, url=url)
