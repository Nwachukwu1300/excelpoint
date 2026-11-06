import json
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from subjects.models import ContentChunk, Flashcard, Question, Quiz, Section, Subject, SubjectMaterial
from subjects.services.sections import build_sections, plan_sections, range_label
from subjects.tests import vec
from subjects.utils import clean_text, extract_text_from_docx

MEDIA = tempfile.mkdtemp()
SENTENCE = 'The light reactions split water and release oxygen while making ATP and NADPH for the next stage. '


def make_pdf(pages, outline=()):
    """A small real PDF: one line of Helvetica text per page, and optional (title, page index) bookmarks."""
    objects = ['<< /Type /Catalog /Pages 2 0 R{outlines} >>', None, '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    page_ids = []
    for text in pages:
        stream = f'BT /F1 9 Tf 20 760 Td ({text.replace("(", "").replace(")", "")}) Tj ET'
        objects.append(f'<< /Length {len(stream)} >>\nstream\n{stream}\nendstream')
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {len(objects)} 0 R >>')
        page_ids.append(len(objects))
    objects[1] = f'<< /Type /Pages /Kids [{" ".join(f"{p} 0 R" for p in page_ids)}] /Count {len(page_ids)} >>'
    outlines = ''
    if outline:
        root = len(objects) + 1
        first = root + 1
        items = [first + i for i in range(len(outline))]
        objects.append(f'<< /Type /Outlines /First {items[0]} 0 R /Last {items[-1]} 0 R /Count {len(items)} >>')
        for i, (title, page) in enumerate(outline):
            links = (f' /Prev {items[i - 1]} 0 R' if i else '') + (f' /Next {items[i + 1]} 0 R' if i + 1 < len(items) else '')
            objects.append(f'<< /Title ({title}) /Parent {root} 0 R /Dest [{page_ids[page]} 0 R /Fit]{links} >>')
        outlines = f' /Outlines {root} 0 R'
    objects[0] = objects[0].format(outlines=outlines)
    out, offsets = b'%PDF-1.4\n', []
    for i, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f'{i} 0 obj\n{body}\nendobj\n'.encode('latin-1')
    xref = len(out)
    out += f'xref\n0 {len(objects) + 1}\n0000000000 65535 f \n'.encode()
    out += ''.join(f'{o:010d} 00000 n \n' for o in offsets).encode()
    out += f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    return out


@override_settings(MEDIA_ROOT=MEDIA, OPENAI_API_KEY='')
class SectionPlanTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = get_user_model().objects.create_user('sec', password='p')
        self.subject = Subject.objects.create(user=self.user, name='Biology')

    def material(self, name, data, file_type):
        m = SubjectMaterial(subject=self.subject, file_type=file_type, status='COMPLETED', original_name=name)
        m.file.save(name, ContentFile(data))
        return m

    def chunk(self, material, text):
        """Passages exactly as processing makes them: cleaned text split 1000/200."""
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        parts = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_text(clean_text(text))
        return [ContentChunk.objects.create(material=material, content=c, chunk_index=i) for i, c in enumerate(parts)]

    def test_word_headings_become_named_sections(self):
        import docx
        document = docx.Document()
        for title, word in (('Light reactions', 'thylakoid'), ('Calvin cycle', 'stroma')):
            document.add_heading(title, 1)
            for _ in range(12):
                document.add_paragraph(f'{SENTENCE}It happens in the {word}.')
        path = f'{MEDIA}/photo.docx'
        document.save(path)
        m = self.material('photo.docx', open(path, 'rb').read(), 'DOCX')
        chunks = self.chunk(m, extract_text_from_docx(m.file.path))
        plans = plan_sections(m, chunks, m.file.path)
        self.assertEqual([(p['title'], p['kind']) for p in plans], [('Light reactions', 'heading'), ('Calvin cycle', 'heading')])
        self.assertEqual(plans[0]['first'], 0)
        self.assertEqual(plans[-1]['last'], len(chunks) - 1)
        self.assertEqual(plans[0]['last'] + 1, plans[1]['first'])  # every passage in exactly one section
        self.assertIn('thylakoid', chunks[plans[0]['first']].content)
        self.assertIn('stroma', chunks[plans[1]['last']].content)

    def test_a_pdf_outline_gives_chapters(self):
        pages = [f'Page {i} {SENTENCE * 6}' for i in range(1, 5)]
        m = self.material('book.pdf', make_pdf(pages, [('Chapter 1 Light', 0), ('Chapter 2 Dark', 2)]), 'PDF')
        from langchain_community.document_loaders import PyPDFLoader
        chunks = self.chunk(m, ' '.join(p.page_content for p in PyPDFLoader(m.file.path).load()))
        plans = plan_sections(m, chunks, m.file.path)
        self.assertEqual([(p['title'], p['start'], p['end']) for p in plans], [('Chapter 1 Light', 1, 2), ('Chapter 2 Dark', 3, 4)])

    def test_a_pdf_without_an_outline_is_grouped_by_pages(self):
        pages = [f'Page {i} {SENTENCE * 6}' for i in range(1, 10)]
        m = self.material('slides.pdf', make_pdf(pages), 'PDF')
        from langchain_community.document_loaders import PyPDFLoader
        chunks = self.chunk(m, ' '.join(p.page_content for p in PyPDFLoader(m.file.path).load()))
        plans = plan_sections(m, chunks, m.file.path)
        self.assertEqual([(p['kind'], p['start'], p['end']) for p in plans], [('pages', 1, 3), ('pages', 4, 6), ('pages', 7, 9)])
        self.assertEqual(range_label(Section(kind='pages', start=4, end=6)), 'Pages 4–6')

    def test_a_one_page_file_is_one_whole_section(self):
        m = self.material('note.pdf', make_pdf([f'Short note {SENTENCE}']), 'PDF')
        from langchain_community.document_loaders import PyPDFLoader
        chunks = self.chunk(m, ' '.join(p.page_content for p in PyPDFLoader(m.file.path).load()))
        self.assertEqual([p['kind'] for p in plan_sections(m, chunks, m.file.path)], ['whole'])

    def test_a_recording_is_split_into_ten_minute_ranges(self):
        m = self.material('lecture.mp3', b'audio', 'AUDIO')
        chunks = [ContentChunk.objects.create(material=m, content=f'part {i}', chunk_index=i) for i in range(10)]
        with patch('subjects.services.sections._duration', return_value=1500):
            plans = plan_sections(m, chunks, m.file.path)
        self.assertEqual([(p['start'], p['end'], p['first'], p['last']) for p in plans], [(0, 600, 0, 3), (600, 1200, 4, 7), (1200, 1500, 8, 9)])
        self.assertEqual(range_label(Section(kind='time', start=1200, end=1500)), 'About 20:00–25:00')
        self.assertEqual(range_label(Section(kind='time', start=3600, end=4200)), 'About 1:00:00–1:10:00')

    def test_passages_that_no_longer_match_the_file_fall_back_to_even_parts(self):
        m = self.material('changed.pdf', make_pdf([f'Page {SENTENCE}']), 'PDF')
        chunks = [ContentChunk.objects.create(material=m, content=f'something else {i}', chunk_index=i) for i in range(20)]
        plans = plan_sections(m, chunks, m.file.path)
        self.assertEqual(len(plans), 5)
        self.assertEqual({p['kind'] for p in plans}, {'part'})
        self.assertEqual((plans[0]['first'], plans[-1]['last']), (0, 19))

    def test_a_big_file_never_has_more_than_15_sections(self):
        m = self.material('big.mp3', b'audio', 'AUDIO')
        chunks = [ContentChunk.objects.create(material=m, content=f'part {i}', chunk_index=i) for i in range(100)]
        with patch('subjects.services.sections._duration', return_value=3 * 3600):
            plans = plan_sections(m, chunks, m.file.path)
        self.assertLessEqual(len(plans), 15)
        self.assertEqual((plans[0]['first'], plans[-1]['last']), (0, 99))


@override_settings(MEDIA_ROOT=MEDIA)
class BuildSectionsTest(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('build', password='p')
        self.subject = Subject.objects.create(user=user, name='Biology')
        # No stored file: the passages are grouped into parts
        self.m = SubjectMaterial.objects.create(subject=self.subject, file='', file_type='PDF', status='COMPLETED', original_name='notes.pdf')
        for i in range(8):
            ContentChunk.objects.create(material=self.m, content=f'passage {i}', chunk_index=i, embedding_vector=vec(1, 0) if i < 4 else vec(0, 1))

    def test_sections_are_named_by_one_ai_call_or_by_their_range(self):
        client = MagicMock()
        client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps({'names': {'0': 'Light reactions.', '1': ''}})))])
        with override_settings(OPENAI_API_KEY='k'), patch('openai.OpenAI', return_value=client):
            sections = build_sections(self.m)
        self.assertEqual([s.title for s in sections], ['Light reactions', 'Part 2 of 2'])
        self.assertEqual([(s.first_chunk, s.last_chunk) for s in sections], [(0, 3), (4, 7)])
        with override_settings(OPENAI_API_KEY=''):
            self.assertEqual([s.title for s in build_sections(self.m)], ['Part 1 of 2', 'Part 2 of 2'])  # rebuilt, not added to
        self.assertEqual(Section.objects.filter(material=self.m).count(), 2)

    @override_settings(OPENAI_API_KEY='')
    def test_cards_and_questions_join_the_section_of_their_nearest_passage(self):
        card = Flashcard.objects.create(subject=self.subject, material=self.m, question='hash buckets?', answer='yes')
        quiz = Quiz.objects.create(subject=self.subject, material=self.m, title='Q')
        question = Question.objects.create(quiz=quiz, text='tree depth?', question_type='short_answer')
        model = MagicMock()
        model.encode.side_effect = lambda texts: np.array([vec(0, 1) if 'hash' in t else vec(1, 0) for t in texts])
        with patch('subjects.services.sections.load_embedding_model', return_value=model):
            first, second = build_sections(self.m)
        card.refresh_from_db()
        question.refresh_from_db()
        self.assertEqual((card.section, question.section), (second, first))
        self.m.delete()
        self.assertFalse(Section.objects.exists())  # deleting the file removes its sections
