"""Celery application bootstrap for the Excelpoint backend.

This module exposes a configured Celery app used by background workers and
scheduled jobs. It reads configuration from Django settings (``CELERY_*``
namespace), auto-discovers tasks across installed Django apps, and applies a
couple of runtime safeguards for local macOS development where some ML
libraries can attempt to use unsupported GPU backends.

Key responsibilities:
- Set the default Django settings module for Celery processes
- Configure the Celery app from ``django.conf.settings``
- Auto-discover ``tasks.py`` modules in installed apps
- Ensure stable CPU-only execution on macOS/Apple Silicon when needed
"""

import os
from celery import Celery
from celery.signals import worker_process_init

# Point Celery at the Django settings so it can read broker/result/backend config
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Ensure deterministic CPU execution for local macOS development
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
os.environ.setdefault('PYTORCH_ENABLE_MPS_FALLBACK', '1')

# Create the Celery application instance
app = Celery('career_nexus')

# Load ``CELERY_*`` configuration values directly from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Discover task modules across installed Django apps
app.autodiscover_tasks()


@worker_process_init.connect
def configure_worker_for_cpu(**kwargs):
    """Harden worker subprocesses for CPU-only execution on macOS.

    Some tokenizer/torch combinations can crash when attempting to use the
    Metal Performance Shaders (MPS) backend on Apple Silicon. We explicitly
    set environment flags for every worker process to prefer CPU execution and
    disable parallel tokenizers to reduce contention.
    """
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Minimal task used to verify worker connectivity and routing.

    Invoking this task should produce a log line with request metadata,
    confirming that the worker is running and can receive tasks from the
    broker.
    """
    print(f'Request: {self.request!r}')