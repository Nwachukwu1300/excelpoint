"""
Django management command for generating missing embeddings.

This command helps backfill embeddings for existing materials that don't have them
or have failed embedding generation.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q, Count
from subjects.models import Subject, SubjectMaterial, ContentChunk
from subjects.tasks import (
    process_subject_embeddings,
    process_material_embeddings,
    update_existing_material_embeddings
)
import logging
import time
from datetime import datetime


class Command(BaseCommand):
    help = 'Generate missing embeddings for subjects, materials, or specific content chunks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--subject-id',
            type=int,
            help='Process embeddings for a specific subject ID'
        )
        
        parser.add_argument(
            '--material-id',
            type=int,
            help='Process embeddings for a specific material ID'
        )
        
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all subjects that have missing or failed embeddings'
        )
        
        parser.add_argument(
            '--failed-only',
            action='store_true',
            help='Only process chunks with failed embedding status'
        )
        
        parser.add_argument(
            '--pending-only',
            action='store_true',
            help='Only process chunks with pending embedding status'
        )
        
        parser.add_argument(
            '--missing-only',
            action='store_true',
            help='Only process chunks that are missing embedding vectors'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually processing'
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of materials to process concurrently (default: 10)'
        )
        
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress detailed output'
        )
        
        parser.add_argument(
            '--stats-only',
            action='store_true',
            help='Only show statistics without processing'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        # Set up logging
        if not options['quiet']:
            logging.basicConfig(level=logging.INFO)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"🚀 Starting embedding backfill process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        )
        
        try:
            # Show overall statistics first
            self._show_system_stats()
            
            if options['stats_only']:
                return
            
            # Validate arguments
            self._validate_arguments(options)
            
            # Process based on options
            if options['subject_id']:
                self._process_subject(options['subject_id'], options)
            elif options['material_id']:
                self._process_material(options['material_id'], options)
            elif options['all']:
                self._process_all_subjects(options)
            else:
                raise CommandError(
                    "Must specify --subject-id, --material-id, or --all"
                )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error during processing: {str(e)}")
            )
            raise CommandError(str(e))
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Embedding backfill process completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        )
    
    def _validate_arguments(self, options):
        """Validate command arguments."""
        filter_count = sum([
            options['failed_only'],
            options['pending_only'],
            options['missing_only']
        ])
        
        if filter_count > 1:
            raise CommandError(
                "Cannot specify multiple filter options (--failed-only, --pending-only, --missing-only)"
            )
    
    def _show_system_stats(self):
        """Show overall system statistics."""
        self.stdout.write(self.style.WARNING("📊 System Statistics:"))
        
        # Count subjects
        total_subjects = Subject.objects.count()
        subjects_with_materials = Subject.objects.filter(materials__isnull=False).distinct().count()
        
        # Count materials
        total_materials = SubjectMaterial.objects.count()
        materials_with_chunks = SubjectMaterial.objects.filter(chunks__isnull=False).distinct().count()
        
        # Count chunks by status
        total_chunks = ContentChunk.objects.count()
        completed_chunks = ContentChunk.objects.filter(embedding_status='completed').count()
        pending_chunks = ContentChunk.objects.filter(embedding_status='pending').count()
        failed_chunks = ContentChunk.objects.filter(embedding_status='failed').count()
        missing_embeddings = ContentChunk.objects.filter(embedding_vector__isnull=True).count()
        
        self.stdout.write(f"  📂 Subjects: {total_subjects} total, {subjects_with_materials} with materials")
        self.stdout.write(f"  📄 Materials: {total_materials} total, {materials_with_chunks} with chunks")
        self.stdout.write(f"  🧩 Content Chunks: {total_chunks} total")
        self.stdout.write(f"    ✅ Completed: {completed_chunks}")
        self.stdout.write(f"    ⏳ Pending: {pending_chunks}")
        self.stdout.write(f"    ❌ Failed: {failed_chunks}")
        self.stdout.write(f"    🔍 Missing vectors: {missing_embeddings}")
        
        if total_chunks > 0:
            completion_rate = (completed_chunks / total_chunks) * 100
            self.stdout.write(f"  📈 Completion rate: {completion_rate:.1f}%")
        
        self.stdout.write("")
    
    def _get_chunk_filter(self, options):
        """Get the appropriate filter for chunks based on options."""
        if options['failed_only']:
            return Q(embedding_status='failed')
        elif options['pending_only']:
            return Q(embedding_status='pending')
        elif options['missing_only']:
            return Q(embedding_vector__isnull=True)
        else:
            # Default: pending, failed, or missing embeddings
            return Q(
                Q(embedding_status__in=['pending', 'failed']) |
                Q(embedding_vector__isnull=True)
            )
    
    def _process_subject(self, subject_id, options):
        """Process embeddings for a specific subject."""
        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            raise CommandError(f"Subject with ID {subject_id} does not exist")
        
        self.stdout.write(
            self.style.WARNING(f"🎯 Processing subject: {subject.name} (ID: {subject_id})")
        )
        
        # Get materials that need processing
        chunk_filter = self._get_chunk_filter(options)
        materials_needing_work = SubjectMaterial.objects.filter(
            subject=subject,
            chunks__in=ContentChunk.objects.filter(chunk_filter)
        ).distinct()
        
        materials_count = materials_needing_work.count()
        
        if materials_count == 0:
            self.stdout.write(
                self.style.SUCCESS(f"✅ No materials need embedding processing in subject: {subject.name}")
            )
            return
        
        self.stdout.write(f"  📄 Found {materials_count} materials needing processing")
        
        if options['dry_run']:
            self._show_materials_detail(materials_needing_work, options)
            self.stdout.write(
                self.style.WARNING("🔍 DRY RUN: No actual processing performed")
            )
            return
        
        # Process the subject
        self.stdout.write(f"  🚀 Queuing embedding processing for subject: {subject.name}")
        task_result = process_subject_embeddings.delay(subject_id)
        
        if not options['quiet']:
            self.stdout.write(f"  ⏳ Task queued with ID: {task_result.id}")
    
    def _process_material(self, material_id, options):
        """Process embeddings for a specific material."""
        try:
            material = SubjectMaterial.objects.get(id=material_id)
        except SubjectMaterial.DoesNotExist:
            raise CommandError(f"Material with ID {material_id} does not exist")
        
        self.stdout.write(
            self.style.WARNING(f"🎯 Processing material: {material.file.name} (ID: {material_id})")
        )
        
        # Get chunks that need processing
        chunk_filter = self._get_chunk_filter(options)
        chunks_needing_work = ContentChunk.objects.filter(
            material=material
        ).filter(chunk_filter)
        
        chunks_count = chunks_needing_work.count()
        
        if chunks_count == 0:
            self.stdout.write(
                self.style.SUCCESS(f"✅ No chunks need embedding processing in material: {material.file.name}")
            )
            return
        
        self.stdout.write(f"  🧩 Found {chunks_count} chunks needing processing")
        
        if options['dry_run']:
            self._show_chunks_detail(chunks_needing_work)
            self.stdout.write(
                self.style.WARNING("🔍 DRY RUN: No actual processing performed")
            )
            return
        
        # Process the material
        self.stdout.write(f"  🚀 Queuing embedding processing for material: {material.file.name}")
        task_result = update_existing_material_embeddings.delay(material_id)
        
        if not options['quiet']:
            self.stdout.write(f"  ⏳ Task queued with ID: {task_result.id}")
    
    def _process_all_subjects(self, options):
        """Process embeddings for all subjects that need work."""
        self.stdout.write(
            self.style.WARNING("🌍 Processing all subjects with missing/failed embeddings")
        )
        
        # Get subjects that have materials with chunks needing work
        chunk_filter = self._get_chunk_filter(options)
        subjects_needing_work = Subject.objects.filter(
            materials__chunks__in=ContentChunk.objects.filter(chunk_filter)
        ).distinct()
        
        subjects_count = subjects_needing_work.count()
        
        if subjects_count == 0:
            self.stdout.write(
                self.style.SUCCESS("✅ No subjects need embedding processing")
            )
            return
        
        self.stdout.write(f"  📂 Found {subjects_count} subjects needing processing")
        
        if options['dry_run']:
            for subject in subjects_needing_work:
                materials_needing_work = SubjectMaterial.objects.filter(
                    subject=subject,
                    chunks__in=ContentChunk.objects.filter(chunk_filter)
                ).distinct()
                
                self.stdout.write(f"  📂 {subject.name}: {materials_needing_work.count()} materials")
            
            self.stdout.write(
                self.style.WARNING("🔍 DRY RUN: No actual processing performed")
            )
            return
        
        # Process subjects in batches
        batch_size = options['batch_size']
        processed_count = 0
        
        for i in range(0, subjects_count, batch_size):
            batch = subjects_needing_work[i:i + batch_size]
            
            self.stdout.write(f"  🚀 Processing batch {i//batch_size + 1} ({len(batch)} subjects)")
            
            for subject in batch:
                task_result = process_subject_embeddings.delay(subject.id)
                processed_count += 1
                
                if not options['quiet']:
                    self.stdout.write(f"    ⏳ Queued {subject.name} (Task: {task_result.id})")
                
                # Small delay to avoid overwhelming the task queue
                time.sleep(0.1)
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ Queued {processed_count} subjects for embedding processing")
        )
    
    def _show_materials_detail(self, materials, options):
        """Show detailed information about materials that would be processed."""
        chunk_filter = self._get_chunk_filter(options)
        
        self.stdout.write("  📋 Materials that would be processed:")
        for material in materials:
            chunks_count = ContentChunk.objects.filter(
                material=material
            ).filter(chunk_filter).count()
            
            self.stdout.write(f"    📄 {material.file.name}: {chunks_count} chunks")
    
    def _show_chunks_detail(self, chunks):
        """Show detailed information about chunks that would be processed."""
        self.stdout.write("  📋 Chunks that would be processed:")
        
        status_counts = chunks.values('embedding_status').annotate(
            count=Count('id')
        ).order_by('embedding_status')
        
        for status_info in status_counts:
            status = status_info['embedding_status']
            count = status_info['count']
            self.stdout.write(f"    🏷️  {status}: {count} chunks")
        
        missing_vectors = chunks.filter(embedding_vector__isnull=True).count()
        if missing_vectors > 0:
            self.stdout.write(f"    🔍 Missing vectors: {missing_vectors} chunks") 