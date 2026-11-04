"""DTOs: the shapes the API accepts and returns. JSON uses camelCase."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    field_serializer,
    field_validator,
)
from pydantic.alias_generators import to_camel

from app.models.product import ProductStatus


def _require_number(value: Any) -> Any:
    """Reject strings and booleans so "price": "10" or true is a type error, not silently coerced."""
    if value is None:
        raise ValueError("must not be null")
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("must be a number")
    return value


# Reusable field types. strip_whitespace trims text before the length checks run.
NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100, strict=True)]
DescriptionStr = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500, strict=True)]
CategoryStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=50, strict=True)]
Price = Annotated[
    Decimal,
    Field(gt=0, max_digits=10, decimal_places=2),
    BeforeValidator(_require_number),
    PlainSerializer(float, return_type=float, when_used="json"),
]
Quantity = Annotated[int, Field(ge=0, le=2_147_483_647, strict=True)]


class _RequestModel(BaseModel):
    # extra="forbid": unknown fields and server-managed fields (id, createdAt, updatedAt) are rejected.
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class ProductCreate(_RequestModel):
    name: NameStr
    description: DescriptionStr | None = None
    price: Price
    quantity: Quantity
    category: CategoryStr
    status: ProductStatus = ProductStatus.ACTIVE

    @field_validator("description")
    @classmethod
    def _blank_description_to_none(cls, value: str | None) -> str | None:
        return value or None


class ProductReplace(ProductCreate):
    """PUT body: the full representation. Omitted optional fields reset to their defaults."""


class ProductPatch(_RequestModel):
    """PATCH body: only the fields sent are changed. Only description may be set to null."""

    # Typed without "| None" on purpose: an explicit null fails validation,
    # while an omitted field keeps the default and is ignored (exclude_unset).
    name: NameStr = None  # type: ignore[assignment]
    description: DescriptionStr | None = None
    price: Price = None  # type: ignore[assignment]
    quantity: Quantity = None  # type: ignore[assignment]
    category: CategoryStr = None  # type: ignore[assignment]
    status: ProductStatus = None  # type: ignore[assignment]

    @field_validator("description")
    @classmethod
    def _blank_description_to_none(cls, value: str | None) -> str | None:
        return value or None


class ProductResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: UUID
    name: str
    description: str | None
    price: Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
    quantity: int
    category: str
    status: ProductStatus
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def _serialize_utc(self, value: datetime) -> str:
        if value.tzinfo is None:  # some databases (e.g. SQLite) drop the zone
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class ProductPage(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: list[ProductResponse]
    page: int
    size: int
    total_items: int
    total_pages: int


class ProductListQuery(BaseModel):
    """Parameters for the list endpoint, already type-checked by the controller."""

    page: int = 1
    size: int = 10
    category: str | None = None
    status: ProductStatus | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    sort: str | None = None
