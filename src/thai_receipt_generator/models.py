from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class DiscountType(Enum):
    NONE = "none"
    ABSOLUTE = "absolute"
    PERCENTAGE = "percentage"


@dataclass
class Discount:
    type: DiscountType = DiscountType.NONE
    value: Decimal = Decimal("0")


@dataclass
class LineItem:
    name: str
    quantity: int = 1
    unit_price: Decimal = Decimal("0")
    has_vat: bool = False
    has_wht: bool = False
    wht_rate: Decimal = Decimal("3")
    discount: Discount = field(default_factory=Discount)


@dataclass
class StandaloneDiscount:
    """A discount row with no quantity/unit price. Always absolute value."""
    name: str = "ส่วนลด"
    amount: Decimal = Decimal("0")


@dataclass
class ReceiptConfig:
    """Full specification of one receipt."""
    items: list[LineItem] = field(default_factory=list)
    standalone_discounts: list[StandaloneDiscount] = field(default_factory=list)

    overall_discount: Discount = field(default_factory=Discount)
    overall_vat: bool = False
    overall_vat_rate: Decimal = Decimal("7")
    overall_wht: bool = False
    overall_wht_rate: Decimal = Decimal("3")

    template_name: str = "formal_invoice"
    variation_id: str = ""


@dataclass
class CalculatedLineItem:
    """A line item with all derived amounts."""
    source: LineItem
    gross_amount: Decimal
    discount_amount: Decimal
    net_amount: Decimal
    vat_amount: Decimal
    wht_amount: Decimal


@dataclass
class ReceiptCalculation:
    """Complete calculated receipt ready for rendering."""
    config: ReceiptConfig
    calculated_items: list[CalculatedLineItem]
    standalone_discounts: list[StandaloneDiscount]

    subtotal: Decimal
    standalone_discount_total: Decimal
    after_standalone: Decimal

    overall_discount_amount: Decimal
    after_overall_discount: Decimal

    per_item_vat_total: Decimal
    per_item_wht_total: Decimal

    overall_vat_amount: Decimal
    overall_wht_amount: Decimal

    total_vat: Decimal
    total_wht: Decimal
    grand_total: Decimal
