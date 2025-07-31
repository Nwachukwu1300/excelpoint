import logging
from typing import Optional, Dict, Any, Tuple
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from ..models import CachedResponse, User, Subject
from django.db import models

logger = logging.getLogger(__name__)


class ChatbotCacheService:
    """
    Service for managing AI chatbot response caching.
    Handles cache lookups, storage, and cleanup operations.
    """
    
    def __init__(self):
        """Initialize the cache service with configuration."""
        self.enabled = getattr(settings, 'CACHE_ENABLED', True)
        self.ttl_hours = getattr(settings, 'CACHE_TTL_HOURS', 48)
        self.max_size = getattr(settings, 'CACHE_MAX_SIZE', 10000)
        self.log_level = getattr(settings, 'CACHE_LOG_LEVEL', 'INFO')
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, self.log_level.upper(), logging.INFO))
    
    def get_cached_response(
        self, 
        user_id: int, 
        subject_id: int, 
        question_text: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a cached response for the given user, subject, and question.
        
        Args:
            user_id: ID of the user making the request
            subject_id: ID of the subject context
            question_text: The question text to look up
            
        Returns:
            Cached response data if found and not expired, None otherwise
        """
        if not self.enabled:
            return None
            
        try:
            # Generate question hash for lookup
            question_hash = CachedResponse.generate_question_hash(question_text)
            
            # Look up cached response
            cached_response = CachedResponse.objects.filter(
                user_id=user_id,
                subject_id=subject_id,
                question_hash=question_hash
            ).first()
            
            if not cached_response:
                self.logger.debug(f"Cache miss for user {user_id}, subject {subject_id}, question: {question_text[:50]}...")
                return None
            
            # Check if expired
            if cached_response.is_expired():
                self.logger.debug(f"Cache expired for user {user_id}, subject {subject_id}, question: {question_text[:50]}...")
                cached_response.delete()
                return None
            
            # Increment hit count and return response
            cached_response.increment_hit_count()
            self.logger.info(f"Cache hit for user {user_id}, subject {subject_id}, question: {question_text[:50]}... (hits: {cached_response.hit_count})")
            
            return cached_response.response_data
            
        except Exception as e:
            self.logger.error(f"Error retrieving cached response: {str(e)}")
            return None
    
    def store_cached_response(
        self, 
        user_id: int, 
        subject_id: int, 
        question_text: str, 
        response_data: Dict[str, Any]
    ) -> bool:
        """
        Store a response in the cache for future use.
        
        Args:
            user_id: ID of the user making the request
            subject_id: ID of the subject context
            question_text: The question text
            response_data: The complete response data to cache
            
        Returns:
            True if successfully stored, False otherwise
        """
        if not self.enabled:
            return False
            
        try:
            # Generate question hash
            question_hash = CachedResponse.generate_question_hash(question_text)
            
            # Calculate expiration time
            expires_at = timezone.now() + timedelta(hours=self.ttl_hours)
            
            # Create or update cache entry
            cached_response, created = CachedResponse.objects.update_or_create(
                user_id=user_id,
                subject_id=subject_id,
                question_hash=question_hash,
                defaults={
                    'question_text': question_text,
                    'response_data': response_data,
                    'expires_at': expires_at,
                    'hit_count': 0,
                }
            )
            
            action = "created" if created else "updated"
            self.logger.info(f"Cache {action} for user {user_id}, subject {subject_id}, question: {question_text[:50]}...")
            
            # Check if we need to clean up old entries
            self._cleanup_if_needed()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing cached response: {str(e)}")
            return False
    
    def _cleanup_if_needed(self):
        """Clean up expired cache entries if we're approaching the size limit."""
        try:
            current_count = CachedResponse.objects.count()
            
            if current_count > self.max_size * 0.9:  # Clean up when 90% full
                self.logger.info(f"Cache cleanup triggered. Current size: {current_count}, Max: {self.max_size}")
                
                # Delete expired entries
                expired_count = CachedResponse.objects.filter(
                    expires_at__lt=timezone.now()
                ).delete()[0]
                
                if expired_count > 0:
                    self.logger.info(f"Cleaned up {expired_count} expired cache entries")
                
                # If still over limit, delete oldest entries
                remaining_count = CachedResponse.objects.count()
                if remaining_count > self.max_size * 0.8:  # Still over 80% full
                    excess_count = remaining_count - int(self.max_size * 0.7)  # Keep 70% full
                    
                    # Delete oldest entries (least recently accessed)
                    oldest_entries = CachedResponse.objects.order_by('last_accessed')[:excess_count]
                    deleted_count = len(oldest_entries)
                    
                    for entry in oldest_entries:
                        entry.delete()
                    
                    self.logger.info(f"Cleaned up {deleted_count} oldest cache entries")
                    
        except Exception as e:
            self.logger.error(f"Error during cache cleanup: {str(e)}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        try:
            total_entries = CachedResponse.objects.count()
            expired_entries = CachedResponse.objects.filter(
                expires_at__lt=timezone.now()
            ).count()
            
            # Get hit count statistics
            hit_stats = CachedResponse.objects.aggregate(
                total_hits=models.Sum('hit_count'),
                avg_hits=models.Avg('hit_count'),
                max_hits=models.Max('hit_count')
            )
            
            return {
                'total_entries': total_entries,
                'expired_entries': expired_entries,
                'active_entries': total_entries - expired_entries,
                'total_hits': hit_stats['total_hits'] or 0,
                'average_hits': hit_stats['avg_hits'] or 0,
                'max_hits': hit_stats['max_hits'] or 0,
                'cache_enabled': self.enabled,
                'ttl_hours': self.ttl_hours,
                'max_size': self.max_size,
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {str(e)}")
            return {}
    
    def clear_user_cache(self, user_id: int) -> int:
        """Clear all cached responses for a specific user."""
        try:
            deleted_count = CachedResponse.objects.filter(user_id=user_id).delete()[0]
            self.logger.info(f"Cleared {deleted_count} cache entries for user {user_id}")
            return deleted_count
        except Exception as e:
            self.logger.error(f"Error clearing cache for user {user_id}: {str(e)}")
            return 0
    
    def clear_subject_cache(self, subject_id: int) -> int:
        """Clear all cached responses for a specific subject."""
        try:
            deleted_count = CachedResponse.objects.filter(subject_id=subject_id).delete()[0]
            self.logger.info(f"Cleared {deleted_count} cache entries for subject {subject_id}")
            return deleted_count
        except Exception as e:
            self.logger.error(f"Error clearing cache for subject {subject_id}: {str(e)}")
            return 0
    
    def cleanup_expired_entries(self) -> int:
        """Manually clean up all expired cache entries."""
        try:
            expired_count = CachedResponse.objects.filter(
                expires_at__lt=timezone.now()
            ).delete()[0]
            
            self.logger.info(f"Manually cleaned up {expired_count} expired cache entries")
            return expired_count
            
        except Exception as e:
            self.logger.error(f"Error during manual cache cleanup: {str(e)}")
            return 0 