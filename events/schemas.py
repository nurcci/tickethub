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
