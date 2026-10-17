import shutil
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from subjects.tests import vec
from subjects.models import ContentChunk, Subject, SubjectMaterial
from subjects.tasks import process_material

MEDIA = tempfile.mkdtemp()
CHUNKS = [
    {'content': 'one', 'chunk_index': 0, 'embedding_vector': vec(0.1)},
    {'content': 'two', 'chunk_index': 1, 'embedding_vector': vec(0.2)},
]


@override_settings(MEDIA_ROOT=MEDIA)
@patch('subjects.tasks.chord')
@patch('subjects.utils.ContentProcessor.process_file', return_value=CHUNKS)
class ProcessMaterialTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def test_reprocessing_replaces_chunks(self, *_):
        user = get_user_model().objects.create_user('u', password='p')
        material = SubjectMaterial(subject=Subject.objects.create(user=user, name='S'), file_type='PDF')
        material.file.save('a.pdf', ContentFile(b'x'))

        process_material(material.id)
        process_material(material.id)

        material.refresh_from_db()
        self.assertEqual(material.status, 'COMPLETED')
        self.assertEqual(list(ContentChunk.objects.filter(material=material).values_list('content', flat=True).order_by('chunk_index')), ['one', 'two'])


from unittest.mock import MagicMock

from subjects.models import Flashcard
from subjects.tasks import generate_quiz_from_material, generate_summary, material_ready
from users.models import Notification


@override_settings(MEDIA_ROOT=MEDIA)
class StudyWorkflowTest(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('w', password='p')
        self.subject = Subject.objects.create(user=user, name='S')
        self.material = SubjectMaterial.objects.create(subject=self.subject, file='subject_materials/notes.pdf',
                                                       file_type='PDF', status='COMPLETED')
        for i, text in enumerate(['DDL defines schema.', 'DML changes rows.']):
            ContentChunk.objects.create(material=self.material, content=text, chunk_index=i, embedding_status='completed')

    @patch('subjects.tasks.chord')
    @patch('subjects.utils.ContentProcessor.process_file', return_value=CHUNKS)
    def test_processing_launches_parallel_workflow_with_callback(self, _, chord):
        process_material(self.material.id)
        header = chord.call_args.args[0]
        self.assertEqual([t.task for t in header.tasks],
                         ['subjects.tasks.generate_flashcards', 'subjects.tasks.generate_quiz_from_material',
                          'subjects.tasks.generate_summary'])
        callback = chord.return_value.call_args.args[0]
        self.assertEqual((callback.task, callback.args), ('subjects.tasks.material_ready', (self.material.id,)))

    @patch('subjects.tasks.OpenAI')
    def test_summary_is_built_from_the_materials_chunks(self, openai):
        openai.return_value.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content='- DDL defines schema'))]
        self.assertEqual(generate_summary(self.material.id)['status'], 'success')
        self.material.refresh_from_db()
        self.assertEqual(self.material.summary, '- DDL defines schema')
        prompt = openai.return_value.chat.completions.create.call_args.kwargs['messages'][1]['content']
        self.assertIn('DDL defines schema.\nDML changes rows.', prompt)

    def test_ready_notification_lists_what_was_made_and_what_failed(self):
        material_ready([{'status': 'success', 'flashcards_created': 5}, {'status': 'error'}, {'status': 'success'}],
                       self.material.id)
        note = Notification.objects.get()
        self.assertEqual(note.title, 'notes.pdf is ready to study')
        self.assertEqual(note.body, "Generated 5 flashcards, a summary. Couldn't create a quiz.")
        self.assertEqual(note.url, f'/subjects/{self.subject.id}/')

    @patch('subjects.tasks._generate_questions_with_openai', return_value=[])
    @patch('subjects.utils.ContentProcessor.process_file')
    def test_quiz_uses_stored_chunks_not_a_reparse(self, process_file, generate):
        generate_quiz_from_material(self.material.id)
        process_file.assert_not_called()
        self.assertIn('DDL defines schema.', generate.call_args.args[0])

    def test_total_failure_is_not_announced_as_ready(self):
        material_ready([{'status': 'error'}] * 3, self.material.id)
        self.assertEqual(Notification.objects.get().title, "Couldn't prepare study aids for notes.pdf")
