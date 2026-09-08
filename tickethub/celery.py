"""Celery-приложение проекта. Настройки берутся из Django settings
(namespace CELERY_* — см. tickethub/settings.py), задачи автоматически
находятся в tasks.py каждого приложения (events/tasks.py).
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tickethub.settings")

app = Celery("tickethub")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
