import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def judge_answer(self, session_pk: int):
    """Run the optional LLM judge on a saved reasoning session."""
    from .evaluation import judge_session
    from .models import ReasoningSession

    try:
        session = ReasoningSession.objects.get(pk=session_pk)
    except ReasoningSession.DoesNotExist:
        return
    try:
        judge_session(session)
    except Exception as e:
        logger.warning(f"LLM judge failed for session {session_pk}: {e}")
        raise self.retry(exc=e, countdown=30)
