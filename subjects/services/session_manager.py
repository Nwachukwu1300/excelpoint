from django.utils import timezone
from django.db import transaction
import logging

from ..models import ChatSession

logger = logging.getLogger(__name__)


class SessionManager:
    """Service class for managing chat session lifecycle with timeout logic"""
    
    DEFAULT_TIMEOUT_MINUTES = 5
    
    def __init__(self, timeout_minutes=None):
        self.timeout_minutes = timeout_minutes or self.DEFAULT_TIMEOUT_MINUTES
    
    def get_or_create_session(self, user, subject, **kwargs):
        """
        Get an active session or create a new one if no active session exists
        or if the existing session has expired.
        
        Args:
            user: User instance
            subject: Subject instance
            **kwargs: Additional fields for session creation
            
        Returns:
            tuple: (ChatSession instance, created: bool)
        """
        # First, check for an existing active session
        active_session = ChatSession.objects.filter(
            user=user,
            subject=subject,
            is_active=True,
            status='active'
        ).first()
        
        if active_session:
            # Check if session has expired
            if self.is_session_active(active_session):
                # Session is still active, extend it and return
                self.extend_session(active_session)
                logger.info(f"Extended active session {active_session.id} for user {user.id}")
                return active_session, False
            else:
                # Session has expired, mark it as such
                self.expire_session(active_session)
                logger.info(f"Expired session {active_session.id} for user {user.id}")
        
        # Create a new session
        with transaction.atomic():
            # Set default title if not provided
            if 'title' not in kwargs and 'content' in kwargs:
                content = kwargs.pop('content')
                kwargs['title'] = content[:50] + '...' if len(content) > 50 else content
            
            new_session = ChatSession.objects.create(
                user=user,
                subject=subject,
                status='active',
                is_active=True,
                last_activity=timezone.now(),
                **kwargs
            )
            
            logger.info(f"Created new session {new_session.id} for user {user.id} and subject {subject.id}")
            return new_session, True
    
    def is_session_active(self, session):
        """
        Check if a session is still active (not expired).
        
        Args:
            session: ChatSession instance
            
        Returns:
            bool: True if session is active, False if expired
        """
        if not session.is_active or session.status != 'active':
            return False
            
        return not session.is_expired(self.timeout_minutes)
    
    def extend_session(self, session):
        """
        Extend a session by updating its last_activity timestamp.
        
        Args:
            session: ChatSession instance
        """
        if session.status == 'active' and session.is_active:
            session.extend_session()
            logger.debug(f"Extended session {session.id}")
    
    def expire_session(self, session):
        """
        Mark a session as expired.
        
        Args:
            session: ChatSession instance
        """
        session.expire_session()
        logger.debug(f"Expired session {session.id}")
    
    def validate_session(self, session_id, user, subject):
        """
        Validate that a session exists, belongs to the user, and is still active.
        
        Args:
            session_id: ID of the session to validate
            user: User instance
            subject: Subject instance
            
        Returns:
            ChatSession instance or None if invalid/expired
        """
        try:
            session = ChatSession.objects.get(
                id=session_id,
                user=user,
                subject=subject
            )
            
            if self.is_session_active(session):
                self.extend_session(session)
                return session
            else:
                self.expire_session(session)
                return None
                
        except ChatSession.DoesNotExist:
            return None
    
    def get_session_history(self, user, subject, limit=30):
        """
        Get chat session history for a user and subject.
        
        Args:
            user: User instance
            subject: Subject instance
            limit: Maximum number of sessions to return
            
        Returns:
            QuerySet of ChatSession instances
        """
        return ChatSession.objects.filter(
            user=user,
            subject=subject
        ).order_by('-updated_at')[:limit] 