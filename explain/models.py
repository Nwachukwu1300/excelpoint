"""Explain it back: the student explains a topic and XP checks each sentence against their files."""

from django.conf import settings
from django.db import models


class ExplainSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='explain_sessions')
    subject = models.ForeignKey('subjects.Subject', on_delete=models.CASCADE, related_name='explain_sessions')
    material = models.ForeignKey('subjects.SubjectMaterial', on_delete=models.SET_NULL, null=True, blank=True)
    section = models.ForeignKey('subjects.Section', on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.CharField(max_length=200)
    # The passages found for the topic at the start: [{chunk_id, material_id, material_name, chunk_index, content}]
    passages = models.JSONField(default=list)
    # Key points from those passages, filled by the first check: [{id, point, chunk_id, covered}]
    key_points = models.JSONField(default=list)
    finished = models.BooleanField(default=False)
    coverage = models.FloatField(null=True, blank=True)  # 0-1, share of key points the student mentioned
    accuracy = models.FloatField(null=True, blank=True)  # 0-1, correct / (correct + wrong)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']


class ExplainCheck(models.Model):
    """One check against the daily limit. Kept apart from sessions so deleting a session doesn't reset the limit;
    it holds no content, and goes with the account."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='explain_checks')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)


class ExplainTurn(models.Model):
    MODES = (('voice', 'Voice'), ('text', 'Text'))
    KINDS = (('explanation', 'Explanation'), ('question', 'Question'), ('off_topic', 'Off topic'))

    session = models.ForeignKey(ExplainSession, on_delete=models.CASCADE, related_name='turns')
    mode = models.CharField(max_length=10, choices=MODES, default='text')
    kind = models.CharField(max_length=20, choices=KINDS, default='explanation')
    student_text = models.TextField()
    reply = models.TextField(blank=True, default='')  # XP's short spoken reply
    answer = models.TextField(blank=True, default='')  # XP's answer when the student asked a question
    # [{sentence, verdict: correct|wrong|not_in_notes, note, chunk_id, material_name, quote}]
    marks = models.JSONField(default=list)
    reasoning_session_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['created_at', 'id']
