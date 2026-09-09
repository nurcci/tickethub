from django.contrib import admin

from .models import Event, Order, Seat, Ticket, Venue


class SeatInline(admin.TabularInline):
    """Позволяет добавлять места прямо со страницы площадки —
    организатору не нужно уходить в отдельный раздел."""

    model = Seat
    extra = 0


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "created_at")
    list_filter = ("city",)
    search_fields = ("name", "city", "address")
    inlines = [SeatInline]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "venue", "starts_at", "created_at")
    list_filter = ("venue__city", "venue")
    search_fields = ("title", "description")
    date_hierarchy = "starts_at"
    autocomplete_fields = ["venue"]


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("venue", "row", "number")
    list_filter = ("venue",)
    search_fields = ("venue__name",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "event", "seat", "buyer_email", "status", "created_at", "paid_at")
    list_filter = ("status", "event")
    search_fields = ("buyer_email",)
    autocomplete_fields = ["event", "seat"]


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("code", "order", "issued_at", "pdf_file")
    search_fields = ("code",)
