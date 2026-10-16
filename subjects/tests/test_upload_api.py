import shutil
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from subjects.models import Subject, SubjectMaterial
from subjects.utils import material_file_type

MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA)
class UploadApiTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_user('u', password='p')
        self.subject = Subject.objects.create(user=self.user, name='S')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = f'/api/subjects/{self.subject.id}/upload_material/'

    @patch('subjects.views.process_material')
    def test_type_comes_from_extension_and_processing_queued_once(self, process):
        response = self.client.post(self.url, {
            'file': SimpleUploadedFile('notes.pdf', b'%PDF'), 'file_type': 'VIDEO',
        })
        self.assertEqual(response.status_code, 201, response.content)
        material = SubjectMaterial.objects.get()
        self.assertEqual(material.file_type, 'PDF')
        process.delay.assert_called_once_with(material.id)

    @patch('subjects.views.process_material')
    def test_unsupported_extension_rejected(self, process):
        response = self.client.post(self.url, {'file': SimpleUploadedFile('x.exe', b'MZ')})
        self.assertEqual(response.status_code, 400)
        process.delay.assert_not_called()

    def test_materials_endpoint_does_not_accept_creates(self):
        response = self.client.post('/api/materials/', {'file': SimpleUploadedFile('a.pdf', b'x')})
        self.assertEqual(response.status_code, 405)

    def test_material_file_type(self):
        self.assertEqual(material_file_type('Lecture.MP4'), 'VIDEO')
        self.assertIsNone(material_file_type('noext'))
