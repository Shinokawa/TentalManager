import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rental_management.settings')

app = Celery('rental_management')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()