from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, PlainSerializer

T = TypeVar("T")

Money = Annotated[
    Decimal,
    PlainSerializer(
        lambda value: float(value or 0),
        return_type=float,
        when_used="json",
    ),
]


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class MessageResponse(BaseModel):
    detail: str
