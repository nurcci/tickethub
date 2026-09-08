"""
URL configuration for tickethub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from events.api import router as events_router

api = NinjaAPI(
    title="TicketHub API",
    version="1.0.0",
    description="Публичный API: список мероприятий, карта мест. "
    "Бронирование мест появится на неделе 3.",
)
api.add_router("/events", events_router)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
