import io
import os
import tempfile

from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.db.models.fields.files import FieldFile
from django.test import SimpleTestCase

from subjects.utils import local_file_path


class RemoteFile:
    """Stands in for an S3 FieldFile: has a name and open(), but no filesystem path."""
    name = 'subject_materials/notes.pdf'

    @property
    def path(self):
        raise NotImplementedError  # same as S3Boto3Storage

    def open(self, mode='rb'):
        return io.BytesIO(b'pdf-bytes')


class _Field:
    def __init__(self, storage):
        self.storage = storage


class LocalFilePathTest(SimpleTestCase):
    def test_remote_storage_is_downloaded_to_temp_file_and_cleaned_up(self):
        with local_file_path(RemoteFile()) as path:
            self.assertTrue(path.endswith('.pdf'))
            with open(path, 'rb') as fh:
                self.assertEqual(fh.read(), b'pdf-bytes')

        self.assertFalse(os.path.exists(path))

    def test_local_storage_uses_real_path(self):
        with tempfile.TemporaryDirectory() as root:
            storage = FileSystemStorage(location=root)
            f = FieldFile(None, _Field(storage), storage.save('a.txt', ContentFile(b'hi')))
            with local_file_path(f) as path:
                self.assertEqual(path, os.path.join(root, 'a.txt'))
            self.assertTrue(os.path.exists(path))
