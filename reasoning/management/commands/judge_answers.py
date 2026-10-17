from django.core.management.base import BaseCommand

from reasoning.evaluation import judge_session
from reasoning.models import ReasoningSession


class Command(BaseCommand):
    help = "Run the LLM judge on answered sessions that don't have a judge evaluation yet"

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50)

    def handle(self, *args, limit, **options):
        sessions = (ReasoningSession.objects
                    .filter(retrieved_chunk_count__gt=0)
                    .exclude(evaluations__evaluator='llm_judge')
                    .order_by('-created_at')[:limit])
        judged = 0
        for session in sessions:
            try:
                e = judge_session(session)
                judged += 1
                self.stdout.write(f"{session.session_id}: relevance={e.answer_relevance} faithfulness={e.faithfulness}")
            except Exception as exc:
                self.stderr.write(f"{session.session_id}: failed ({exc})")
        self.stdout.write(self.style.SUCCESS(f"Judged {judged} session(s)"))
