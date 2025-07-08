from rest_framework import permissions
from django.shortcuts import get_object_or_404
from .models import Subject, ChatSession


class IsSubjectOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a subject to access its resources.
    
    This permission checks if the authenticated user owns the subject
    that is being accessed through the API.
    """
    
    message = "You do not have permission to access this subject."
    
    def has_permission(self, request, view):
        """
        Check if user is authenticated and has basic permissions.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers have access to all subjects
        if request.user.is_superuser:
            return True
        
        # Check if subject_id is in URL kwargs
        subject_id = view.kwargs.get('subject_id') or view.kwargs.get('subject_pk')
        if not subject_id:
            # If no subject_id in URL, let the view handle it
            return True
        
        try:
            subject = Subject.objects.get(id=subject_id)
            return subject.user == request.user
        except Subject.DoesNotExist:
            return False
    
    def has_object_permission(self, request, view, obj):
        """
        Check object-level permissions for subject-related resources.
        """
        # Superusers have access to all objects
        if request.user.is_superuser:
            return True
        
        # Handle different object types
        if isinstance(obj, Subject):
            return obj.user == request.user
        elif isinstance(obj, ChatSession):
            return obj.user == request.user
        elif hasattr(obj, 'session'):  # ChatMessage
            return obj.session.user == request.user
        elif hasattr(obj, 'subject'):  # SubjectMaterial, ContentChunk, etc.
            return obj.subject.user == request.user
        
        # Default to checking if the user owns the related subject
        return False


class IsChatSessionOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a chat session to access it.
    
    This permission specifically handles chat session access control.
    """
    
    message = "You do not have permission to access this chat session."
    
    def has_permission(self, request, view):
        """
        Check if user is authenticated and can access the chat session.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers have access to all sessions
        if request.user.is_superuser:
            return True
        
        # Check if session_id is in URL kwargs
        session_id = view.kwargs.get('session_id') or view.kwargs.get('session_pk')
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id)
                return session.user == request.user
            except ChatSession.DoesNotExist:
                return False
        
        # Check if subject_id is provided (for creating new sessions)
        subject_id = view.kwargs.get('subject_id') or view.kwargs.get('subject_pk')
        if subject_id:
            try:
                subject = Subject.objects.get(id=subject_id)
                return subject.user == request.user
            except Subject.DoesNotExist:
                return False
        
        # If neither session_id nor subject_id, let the view handle it
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        Check object-level permissions for chat session related resources.
        """
        # Superusers have access to all objects
        if request.user.is_superuser:
            return True
        
        if isinstance(obj, ChatSession):
            return obj.user == request.user
        elif hasattr(obj, 'session'):  # ChatMessage
            return obj.session.user == request.user
        
        return False


class IsAuthenticatedAndOwner(permissions.BasePermission):
    """
    Combined permission that checks authentication and ownership.
    
    This is a convenience permission that combines IsAuthenticated
    with ownership checking for various subject-related resources.
    """
    
    message = "Authentication required and you must own this resource."
    
    def has_permission(self, request, view):
        """
        Check if user is authenticated.
        """
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Check if the user owns the object.
        """
        # Superusers have access to all objects
        if request.user.is_superuser:
            return True
        
        # Check ownership based on object type
        if isinstance(obj, Subject):
            return obj.user == request.user
        elif isinstance(obj, ChatSession):
            return obj.user == request.user
        elif hasattr(obj, 'session'):  # ChatMessage
            return obj.session.user == request.user
        elif hasattr(obj, 'subject'):  # SubjectMaterial, ContentChunk, etc.
            return obj.subject.user == request.user
        elif hasattr(obj, 'user'):  # Any object with direct user relationship
            return obj.user == request.user
        
        # Default deny
        return False


class ChatAPIPermission(permissions.BasePermission):
    """
    Specialized permission for XP chatbot API endpoints.
    
    This permission handles all the specific cases for chat API access,
    including subject ownership, session management, and message creation.
    """
    
    message = "You do not have permission to use the chat API for this subject."
    
    def has_permission(self, request, view):
        """
        Check permissions for chat API endpoints.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers always have permission
        if request.user.is_superuser:
            return True
        
        # For chat endpoints, we need either subject_id or session_id
        subject_id = view.kwargs.get('subject_id') or view.kwargs.get('subject_pk')
        session_id = view.kwargs.get('session_id') or view.kwargs.get('session_pk')
        
        # Check subject ownership if subject_id is provided
        if subject_id:
            try:
                subject = Subject.objects.get(id=subject_id)
                return subject.user == request.user
            except Subject.DoesNotExist:
                return False
        
        # Check session ownership if session_id is provided
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id)
                return session.user == request.user
            except ChatSession.DoesNotExist:
                return False
        
        # If we have a POST request with session data in the body
        if request.method == 'POST' and hasattr(request, 'data'):
            session_id_in_data = request.data.get('session_id') or request.data.get('session')
            if session_id_in_data:
                try:
                    session = ChatSession.objects.get(id=session_id_in_data)
                    return session.user == request.user
                except (ChatSession.DoesNotExist, ValueError):
                    pass
        
        # Default to True for endpoints that don't specify subject/session
        # Let the view handle the specific logic
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        Object-level permission checking for chat API.
        """
        if request.user.is_superuser:
            return True
        
        if isinstance(obj, ChatSession):
            return obj.user == request.user
        elif hasattr(obj, 'session'):  # ChatMessage
            return obj.session.user == request.user
        elif hasattr(obj, 'subject'):  # Subject-related objects
            return obj.subject.user == request.user
        
        return False 