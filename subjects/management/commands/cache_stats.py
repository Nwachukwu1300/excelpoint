from django.core.management.base import BaseCommand
from subjects.services.cache_service import ChatbotCacheService
from subjects.models import CachedResponse
from django.db.models import Count, Avg, Max, Min, Sum
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Show AI chatbot response cache statistics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed statistics including top users and subjects',
        )
        parser.add_argument(
            '--user',
            type=int,
            help='Show statistics for specific user ID only',
        )
        parser.add_argument(
            '--subject',
            type=int,
            help='Show statistics for specific subject ID only',
        )

    def handle(self, *args, **options):
        cache_service = ChatbotCacheService()
        
        if not cache_service.enabled:
            self.stdout.write(
                self.style.WARNING('Cache is disabled.')
            )
            return
        
        self.stdout.write('AI Chatbot Response Cache Statistics')
        self.stdout.write('=' * 50)
        
        # Basic stats
        stats = cache_service.get_cache_stats()
        
        self.stdout.write(f'Cache Status: {"ENABLED" if stats.get("cache_enabled") else "DISABLED"}')
        self.stdout.write(f'TTL: {stats.get("ttl_hours", 0)} hours')
        self.stdout.write(f'Max Size: {stats.get("max_size", 0):,} entries')
        self.stdout.write('')
        
        self.stdout.write('Current State:')
        self.stdout.write(f'  Total Entries: {stats.get("total_entries", 0):,}')
        self.stdout.write(f'  Active Entries: {stats.get("active_entries", 0):,}')
        self.stdout.write(f'  Expired Entries: {stats.get("expired_entries", 0):,}')
        self.stdout.write('')
        
        self.stdout.write('Performance:')
        self.stdout.write(f'  Total Hits: {stats.get("total_hits", 0):,}')
        self.stdout.write(f'  Average Hits: {stats.get("average_hits", 0):.2f}')
        self.stdout.write(f'  Max Hits: {stats.get("max_hits", 0):,}')
        
        if stats.get("total_entries", 0) > 0:
            hit_rate = (stats.get("total_hits", 0) / stats.get("total_entries", 1)) * 100
            self.stdout.write(f'  Hit Rate: {hit_rate:.2f}%')
        
        self.stdout.write('')
        
        # Filter by user or subject if specified
        queryset = CachedResponse.objects.all()
        if options['user']:
            queryset = queryset.filter(user_id=options['user'])
            self.stdout.write(f'Filtered by User ID: {options["user"]}')
        elif options['subject']:
            queryset = queryset.filter(subject_id=options['subject'])
            self.stdout.write(f'Filtered by Subject ID: {options["subject"]}')
        
        # Recent activity
        recent_entries = queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        recent_hits = queryset.filter(
            last_accessed__gte=timezone.now() - timedelta(days=7)
        ).aggregate(total_hits=Sum('hit_count'))['total_hits'] or 0
        
        self.stdout.write('Recent Activity (Last 7 Days):')
        self.stdout.write(f'  New Entries: {recent_entries:,}')
        self.stdout.write(f'  Hits: {recent_hits:,}')
        self.stdout.write('')
        
        if options['detailed']:
            self.stdout.write('Detailed Statistics:')
            self.stdout.write('-' * 30)
            
            # Top users by cache entries
            top_users = queryset.values('user__username').annotate(
                entry_count=Count('id'),
                total_hits=Sum('hit_count')
            ).order_by('-entry_count')[:10]
            
            self.stdout.write('Top Users by Cache Entries:')
            for user in top_users:
                self.stdout.write(f'  {user["user__username"]}: {user["entry_count"]} entries, {user["total_hits"]} hits')
            
            self.stdout.write('')
            
            # Top subjects by cache entries
            top_subjects = queryset.values('subject__name').annotate(
                entry_count=Count('id'),
                total_hits=Sum('hit_count')
            ).order_by('-entry_count')[:10]
            
            self.stdout.write('Top Subjects by Cache Entries:')
            for subject in top_subjects:
                self.stdout.write(f'  {subject["subject__name"]}: {subject["entry_count"]} entries, {subject["total_hits"]} hits')
            
            self.stdout.write('')
            
            # Most popular cached responses
            popular_responses = queryset.order_by('-hit_count')[:10]
            
            self.stdout.write('Most Popular Cached Responses:')
            for response in popular_responses:
                question_preview = response.question_text[:50] + "..." if len(response.question_text) > 50 else response.question_text
                self.stdout.write(f'  "{question_preview}" - {response.hit_count} hits')
            
            self.stdout.write('')
            
            # Age distribution
            now = timezone.now()
            age_ranges = [
                ('Last Hour', now - timedelta(hours=1)),
                ('Last 24 Hours', now - timedelta(days=1)),
                ('Last Week', now - timedelta(days=7)),
                ('Last Month', now - timedelta(days=30)),
                ('Older', None)
            ]
            
            self.stdout.write('Age Distribution:')
            for label, cutoff in age_ranges:
                if cutoff:
                    count = queryset.filter(created_at__gte=cutoff).count()
                else:
                    count = queryset.filter(created_at__lt=age_ranges[-2][1]).count()
                self.stdout.write(f'  {label}: {count:,} entries')
        
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS('Cache statistics retrieved successfully.')
        ) 