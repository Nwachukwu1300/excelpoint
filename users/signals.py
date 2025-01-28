from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal to handle additional setup when a user is created.
    """
    if created:
        # Add any additional setup needed when a user is created for example, you might want to automatically set up a profile page or send a welcome email when someone registers.
        pass