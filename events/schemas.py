"""Pydantic-схемы для API (через ninja.Schema — это обёртка над Pydantic).

Эти же схемы автоматически превращаются в OpenAPI/Swagger — отдельно
документацию писать не нужно, она генерируется из типов.
"""

import datetime

from ninja import Schema


class VenueOut(Schema):
    id: int
    name: str
    city: str
    address: str


class EventOut(Schema):
    id: int
    title: str
    description: str
    starts_at: datetime.datetime
    venue: VenueOut


class SeatOut(Schema):
    id: int
    row: int
    number: int
    is_available: bool


class EventSeatMapOut(Schema):
    event: EventOut
    seats: list[SeatOut]


class HoldSeatIn(Schema):
    buyer_email: str


class HoldSeatOut(Schema):
    order_id: int
    status: str
    event_id: int
    seat_id: int
    hold_expires_at: datetime.datetime


class ErrorOut(Schema):
    detail: str


class PaymentAcceptedOut(Schema):
    order_id: int
    status: str


class OrderOut(Schema):
    order_id: int
    status: str
    event_id: int
    seat_id: int
    buyer_email: str
    ticket_code: str | None = None
    ticket_pdf_url: str | None = None
