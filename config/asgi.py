"""ASGI entrypoint for the Excelpoint Django project.

This module exposes the ``application`` callable used by ASGI servers
such as Daphne, Uvicorn, or Hypercorn. It is the gateway for any
asynchronous protocol support (HTTP, WebSocket, etc.).

Most deployments of this project use WSGI for synchronous HTTP; this
ASGI configuration is included to make it easy to add real-time or
async features in the future without changing the server bootstrap.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
