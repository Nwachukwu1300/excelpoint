"""Quiz attempts for the app: what the student may see, grading, and the review afterwards.

Static quizzes keep their questions in Question/Choice/Answer rows; "fresh" attempts get LLM-written
questions stored on the attempt (dynamic_questions JSON). These helpers treat both the same way.
"""

from ..models import UserAnswer
from ..utils import short_answer_matches

CHOICE_TYPES = ('multiple_choice', 'true_false')


def attempt_status(attempt):
    """generating → ready (or failed) → completed. `dynamic_questions` is None while the job runs, [] if it gave up."""
    if attempt.is_completed:
        return 'completed' if attempt.score is not None else 'abandoned'
    if attempt.uses_dynamic_questions:
        if attempt.dynamic_questions is None:
            return 'generating'
        if attempt.dynamic_questions == []:
            return 'failed'
    return 'ready'


def public_questions(attempt):
    """Questions as the student sees them while answering: never which choice is right."""
    return [
        {
            'id': str(q['id']), 'text': q['text'], 'type': q['type'], 'points': q.get('points', 1),
            'choices': [{'id': str(c['id']), 'text': c['text']} for c in q.get('choices', [])] if q['type'] in CHOICE_TYPES else [],
        }
        for q in attempt.get_questions()
    ]


def _correct_text(q):
    if q['type'] in CHOICE_TYPES:
        return ', '.join(c['text'] for c in q.get('choices', []) if c.get('is_correct'))
    return (q.get('correct_answers') or [''])[0]


def grade(attempt, answers):
    """Mark every question, store the answers and finish the attempt. `answers` maps question id → choice id or text."""
    answers = {str(k): str(v).strip() for k, v in (answers or {}).items() if v is not None}
    if attempt.uses_dynamic_questions and attempt.dynamic_questions:
        graded = []
        for q in attempt.dynamic_questions:
            given = answers.get(str(q['id']), '')
            if q['type'] in CHOICE_TYPES:
                choice = next((c for c in q.get('choices', []) if str(c['id']) == given), None)
                shown, correct = (choice['text'], bool(choice.get('is_correct'))) if choice else ('', False)
            else:
                shown, correct = given, bool(given) and short_answer_matches(given, q.get('correct_answers', []))
            if shown:
                UserAnswer.objects.create(attempt=attempt, question=None, answer_text=f"Q: {q['text']}\nA: {shown}", is_correct=correct)
            graded.append({**q, 'user_answer': shown, 'is_correct': correct})
        attempt.dynamic_questions = graded  # the review reads each answer back from here
    else:
        for q in attempt.quiz.questions.prefetch_related('choices', 'answers'):
            given = answers.get(str(q.id), '')
            if not given:
                continue
            choice = None
            if q.question_type in CHOICE_TYPES:
                choice = next((c for c in q.choices.all() if str(c.id) == given), None)
                shown, correct = (choice.text, choice.is_correct) if choice else ('', False)
            else:
                shown = given
                correct = short_answer_matches(given, [a.text for a in q.answers.all() if a.is_correct])
            if shown:
                UserAnswer.objects.create(attempt=attempt, question=q, selected_choice=choice, answer_text=shown, is_correct=correct)
    attempt.complete_attempt()  # end time + score over every question (unanswered ones earn nothing)
    return attempt


def review(attempt):
    """Each question with the student's answer, the right answer and the explanation (only after finishing)."""
    rows = []
    if attempt.uses_dynamic_questions and attempt.dynamic_questions:
        older = list(attempt.user_answers.filter(question__isnull=True))  # attempts graded before answers lived in the JSON
        for q in attempt.dynamic_questions:
            if 'is_correct' in q:
                yours, correct = q.get('user_answer', ''), q['is_correct']
            else:
                match = next((a for a in older if (a.answer_text or '').startswith(f"Q: {q['text']}\n")), None)
                yours = match.answer_text.split('\nA: ', 1)[-1] if match else ''
                correct = bool(match and match.is_correct)
            rows.append({'id': str(q['id']), 'text': q['text'], 'type': q['type'], 'points': q.get('points', 1),
                         'your_answer': yours, 'correct_answer': _correct_text(q), 'is_correct': correct,
                         'explanation': q.get('explanation', '')})
    else:
        given = {a.question_id: a for a in attempt.user_answers.filter(question__isnull=False)}
        for q in attempt.quiz.questions.prefetch_related('choices', 'answers').order_by('order'):
            if q.question_type in CHOICE_TYPES:
                right = ', '.join(c.text for c in q.choices.all() if c.is_correct)
            else:
                right = next((a.text for a in q.answers.all() if a.is_correct), '')
            a = given.get(q.id)
            rows.append({'id': str(q.id), 'text': q.text, 'type': q.question_type, 'points': q.points,
                         'your_answer': a.answer_text if a else '', 'correct_answer': right,
                         'is_correct': bool(a and a.is_correct), 'explanation': q.explanation})
    return rows
