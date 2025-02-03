from django.db import models
from django.conf import settings

class Job(models.Model):
    """
    Model for job listings in CareerNexus.
    """
    EMPLOYMENT_TYPE = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('freelance', 'Freelance'),
        ('internship', 'Internship'),
    ]

    title = models.CharField(
        max_length=200,
        help_text="Job position title"
    )
    
    company = models.CharField(
        max_length=200,
        help_text="Company offering the position"
    )
    
    description = models.TextField(
        help_text="Detailed job description"
    )
    
    employment_type = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_TYPE,
        help_text="Type of employment offered"
    )
    
    location = models.CharField(
        max_length=200,
        help_text="Job location or 'Remote'"
    )
    
    salary_range = models.CharField(
        max_length=100,
        blank=True,
        help_text="Expected salary range"
    )
    
    required_skills = models.ManyToManyField(
        'skills.Skill',
        related_name='required_for_jobs',
        help_text="Skills required for this position"
    )
    
    posted_date = models.DateTimeField(
        auto_now_add=True,
        help_text="When the job was posted"
    )

    def __str__(self):
        return f"{self.title} at {self.company}"