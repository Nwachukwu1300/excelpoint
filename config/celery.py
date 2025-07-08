import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Fix for macOS + Apple Silicon + sentence transformers issues
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
os.environ.setdefault('PYTORCH_ENABLE_MPS_FALLBACK', '1')

app = Celery('career_nexus')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Worker initialization to prevent MPS issues
from celery.signals import worker_process_init

@worker_process_init.connect
def configure_worker_for_cpu(**kwargs):
    """Configure worker to use CPU instead of MPS to prevent crashes on macOS."""
    import os
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 