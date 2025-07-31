from django.core.management.base import BaseCommand
from django.utils import timezone
from subjects.services.cache_service import ChatbotCacheService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up expired AI chatbot response cache entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force cleanup even if not scheduled',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually doing it',
        )
        parser.add_argument(
            '--user',
            type=int,
            help='Clean up cache for specific user ID only',
        )
        parser.add_argument(
            '--subject',
            type=int,
            help='Clean up cache for specific subject ID only',
        )

    def handle(self, *args, **options):
        cache_service = ChatbotCacheService()
        
        if not cache_service.enabled:
            self.stdout.write(
                self.style.WARNING('Cache is disabled. No cleanup needed.')
            )
            return
        
        self.stdout.write('Starting cache cleanup...')
        
        if options['dry_run']:
            self.stdout.write('DRY RUN MODE - No changes will be made')
            
            # Count expired entries
            from subjects.models import CachedResponse
            expired_count = CachedResponse.objects.filter(
                expires_at__lt=timezone.now()
            ).count()
            
            if options['user']:
                expired_count = CachedResponse.objects.filter(
                    user_id=options['user'],
                    expires_at__lt=timezone.now()
                ).count()
                self.stdout.write(f'Would clean up {expired_count} expired entries for user {options["user"]}')
            elif options['subject']:
                expired_count = CachedResponse.objects.filter(
                    subject_id=options['subject'],
                    expires_at__lt=timezone.now()
                ).count()
                self.stdout.write(f'Would clean up {expired_count} expired entries for subject {options["subject"]}')
            else:
                self.stdout.write(f'Would clean up {expired_count} expired entries')
            
            return
        
        # Perform actual cleanup
        if options['user']:
            deleted_count = cache_service.clear_user_cache(options['user'])
            self.stdout.write(
                self.style.SUCCESS(f'Cleaned up {deleted_count} cache entries for user {options["user"]}')
            )
        elif options['subject']:
            deleted_count = cache_service.clear_subject_cache(options['subject'])
            self.stdout.write(
                self.style.SUCCESS(f'Cleaned up {deleted_count} cache entries for subject {options["subject"]}')
            )
        else:
            deleted_count = cache_service.cleanup_expired_entries()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully cleaned up {deleted_count} expired cache entries')
            )
        
        # Show cache stats
        stats = cache_service.get_cache_stats()
        self.stdout.write('\nCache Statistics:')
        self.stdout.write(f'  Total entries: {stats.get("total_entries", 0)}')
        self.stdout.write(f'  Active entries: {stats.get("active_entries", 0)}')
        self.stdout.write(f'  Expired entries: {stats.get("expired_entries", 0)}')
        self.stdout.write(f'  Total hits: {stats.get("total_hits", 0)}')
        self.stdout.write(f'  Average hits: {stats.get("average_hits", 0):.2f}')
        self.stdout.write(f'  Max hits: {stats.get("max_hits", 0)}') 