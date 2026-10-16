from django.contrib.auth import get_user_model
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from subjects.models import CachedResponse, Subject, SubjectMaterial


class CacheInvalidationTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('u', password='p')
        self.subject = Subject.objects.create(user=self.user, name='S')
        self.other = Subject.objects.create(user=self.user, name='Other')

    def cache(self, subject):
        return CachedResponse.objects.create(
            user=self.user, subject=subject, question_hash=f'h{subject.id}',
            question_text='q', response_data={}, expires_at=timezone.now() + timedelta(hours=1),
        )

    def test_material_change_clears_only_that_subjects_cache(self):
        material = SubjectMaterial.objects.create(subject=self.subject, file='a.pdf', file_type='PDF')
        self.cache(self.subject)
        kept = self.cache(self.other)

        material.status = 'COMPLETED'
        material.save()
        self.assertFalse(CachedResponse.objects.filter(subject=self.subject).exists())

        self.cache(self.subject)
        material.delete()
        self.assertFalse(CachedResponse.objects.filter(subject=self.subject).exists())
        self.assertTrue(CachedResponse.objects.filter(pk=kept.pk).exists())
