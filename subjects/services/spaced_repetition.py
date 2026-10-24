"""Spaced-repetition queries: which flashcards are due, and recording a review."""

from django.db.models import Q
from django.utils import timezone

from ..models import Flashcard, FlashcardReview


# The four buttons people grade with (SM-2 grades; below 3 counts as forgotten)
REVIEW_GRADES = [(1, 'Again'), (3, 'Hard'), (4, 'Good'), (5, 'Easy')]


def due_cards(user, subject=None):
    """Cards due now for this user: never reviewed, or past their due date. Overdue first, then new."""
    cards = Flashcard.objects.filter(subject__user=user)
    if subject is not None:
        cards = cards.filter(subject=subject)
    reviewed = FlashcardReview.objects.filter(user=user)
    return (cards
            .filter(~Q(id__in=reviewed.values('flashcard_id')) | Q(id__in=reviewed.filter(due_at__lte=timezone.now()).values('flashcard_id')))
            .order_by('reviews__due_at', 'created_at'))


def preview_intervals(review):
    """Days until the card comes back for each grade, without changing or saving `review`."""
    out = {}
    for grade, _ in REVIEW_GRADES:
        trial = FlashcardReview(repetitions=review.repetitions, interval_days=review.interval_days, ease=review.ease)
        trial.apply_grade(grade)
        out[grade] = trial.interval_days
    return out


def record_review(user, flashcard, grade):
    review, _ = FlashcardReview.objects.get_or_create(user=user, flashcard=flashcard)
    review.apply_grade(grade)
    review.save()
    return review
