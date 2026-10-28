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


@override_settings(MEDIA_ROOT=MEDIA)
@patch('subjects.views.process_material')
class UploadChecksTest(TestCase):
    """Files the server can't read are refused at upload with a reason, not left to fail later."""

    def setUp(self):
        user = get_user_model().objects.create_user('c', password='p')
        self.subject = Subject.objects.create(user=user, name='S')
        self.client = APIClient()
        self.client.force_authenticate(user)
        self.url = f'/api/subjects/{self.subject.id}/upload_material/'

    def upload(self, name, content):
        return self.client.post(self.url, {'file': SimpleUploadedFile(name, content)})

    def test_refusals_say_why(self, process):
        cases = [
            ('junk.pdf', b'just some text', "isn't a readable PDF"),
            ('notes.docx', b'plain text', "isn't a readable Word (.docx)"),
            ('old.doc', b'\xd0\xcf\x11\xe0', 'Save it as .docx or PDF'),
            ('talk.mp4', b'\x00\x00\x00\x18ftyp', "Audio and video aren't supported yet"),
            ('run.exe', b'MZ', "isn't supported"),
        ]
        for name, content, reason in cases:
            with self.subTest(name=name):
                response = self.upload(name, content)
                self.assertEqual(response.status_code, 400)
                self.assertIn(reason, response.json()['file'][0])
        self.assertFalse(SubjectMaterial.objects.exists())
        process.delay.assert_not_called()

    def test_checks_work_where_pydub_cannot_import(self, process):
        import sys
        with patch.dict(sys.modules, {'pydub': None, 'subjects.services.transcription_service': None}):
            response = self.upload('talk.mp4', b'\x00\x00\x00\x18ftyp')
        self.assertEqual(response.status_code, 400)  # CI has no audioop: this was a 500

    def test_shows_the_uploaded_name_not_the_stored_one(self, process):
        first = self.upload('notes.pdf', b'%PDF-1.4').json()
        second = self.upload('notes.pdf', b'%PDF-1.4').json()
        self.assertEqual([first['filename'], second['filename']], ['notes.pdf', 'notes.pdf'])
        stored = list(SubjectMaterial.objects.values_list('file', flat=True))
        self.assertEqual(len(set(stored)), 2)  # storage still keeps two separate files
