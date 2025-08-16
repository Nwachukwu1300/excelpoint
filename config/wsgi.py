"""WSGI entrypoint for the Excelpoint Django project.

This module exposes the ``application`` object that WSGI-compliant web
servers (e.g., Gunicorn, uWSGI) import to serve HTTP traffic. In this
project, WSGI is the default deployment target for synchronous views.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
