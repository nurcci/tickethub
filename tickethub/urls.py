"""
URL configuration for tickethub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path
from django.views.generic import RedirectView
from django.views.static import serve as serve_static
from ninja import NinjaAPI

from events.api import router as events_router
from events.api_orders import router as orders_router

api = NinjaAPI(
    title="TicketHub API",
    version="1.0.0",
    description=(
        "Публичный API: список мероприятий, карта мест, бронирование места "
        "(Redis SETNX + TTL, /events/{id}/seats/{id}/hold) и оплата заказа "
        "с асинхронным выпуском PDF-билета через Celery (/orders/{id}/pay)."
    ),
)
api.add_router("/events", events_router)
api.add_router("/orders", orders_router)

urlpatterns = [
    path("", RedirectView.as_view(url="/api/docs", permanent=False)),
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]

# Раздаём PDF-билеты через сам Django — в том числе и в проде (неделя 5).
# Обычно так не делают (media в проде — задача nginx/S3/CDN), но здесь
# это осознанное упрощение: один бесплатный инстанс без выделенного
# файлового хранилища, трафик пет-проекта копеечный. Используем
# django.views.static.serve напрямую, а не шорткат static() из
# django.conf.urls.static — тот сам отказывается работать при
# DEBUG=False, а нам как раз нужно, чтобы билеты открывались и в проде.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve_static, {"document_root": settings.MEDIA_ROOT}),
]
