from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .models import (
    CalculatedLineItem,
    Discount,
    DiscountType,
    LineItem,
    ReceiptCalculation,
    ReceiptConfig,
    ReceiptRow,
    StandaloneDiscount,
)

TWO_PLACES = Decimal("0.01")


def _round(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _calc_discount(gross: Decimal, discount: Discount) -> Decimal:
    if discount.type == DiscountType.ABSOLUTE:
        return _round(discount.value)
    if discount.type == DiscountType.PERCENTAGE:
        return _round(gross * discount.value / Decimal("100"))
    return Decimal("0")


def _calc_line_item(item: LineItem) -> CalculatedLineItem:
    gross = _round(Decimal(str(item.quantity)) * item.unit_price)
    discount_amount = min(_calc_discount(gross, item.discount), gross)
    net = gross - discount_amount

    vat = _round(net * Decimal("7") / Decimal("100")) if item.has_vat else Decimal("0")
    wht = _round(net * item.wht_rate / Decimal("100")) if item.has_wht else Decimal("0")

    return CalculatedLineItem(
        source=item,
        gross_amount=gross,
        discount_amount=discount_amount,
        net_amount=net,
        vat_amount=vat,
        wht_amount=wht,
    )


def calculate(config: ReceiptConfig) -> ReceiptCalculation:
    calculated_items = [_calc_line_item(item) for item in config.items]

    subtotal = sum((ci.net_amount for ci in calculated_items), Decimal("0"))
    standalone_discount_total = min(
        sum((sd.amount for sd in config.standalone_discounts), Decimal("0")),
        subtotal,
    )
    after_standalone = subtotal - standalone_discount_total

    overall_discount_amount = min(
        _calc_discount(after_standalone, config.overall_discount),
        after_standalone,
    )
    after_overall_discount = after_standalone - overall_discount_amount

    per_item_vat_total = sum((ci.vat_amount for ci in calculated_items), Decimal("0"))
    per_item_wht_total = sum((ci.wht_amount for ci in calculated_items), Decimal("0"))

    overall_vat = (
        _round(after_overall_discount * config.overall_vat_rate / Decimal("100"))
        if config.overall_vat
        else Decimal("0")
    )
    overall_wht = (
        _round(after_overall_discount * config.overall_wht_rate / Decimal("100"))
        if config.overall_wht
        else Decimal("0")
    )

    total_vat = per_item_vat_total + overall_vat
    total_wht = per_item_wht_total + overall_wht
    grand_total = after_overall_discount + total_vat - total_wht

    # Build interleaved row list: items + standalone discounts in display order
    rows: list[ReceiptRow] = []
    sd_by_pos: dict[int, list[StandaloneDiscount]] = {}
    end_sds: list[StandaloneDiscount] = []
    for sd in config.standalone_discounts:
        if sd.position < 0 or sd.position >= len(calculated_items):
            end_sds.append(sd)
        else:
            sd_by_pos.setdefault(sd.position, []).append(sd)

    for i, ci in enumerate(calculated_items):
        # Insert standalone discounts positioned before this item
        for sd in sd_by_pos.get(i, []):
            rows.append(sd)
        rows.append(ci)
    # Standalone discounts positioned after all items
    for sd in end_sds:
        rows.append(sd)

    return ReceiptCalculation(
        config=config,
        calculated_items=calculated_items,
        standalone_discounts=list(config.standalone_discounts),
        rows=rows,
        subtotal=subtotal,
        standalone_discount_total=standalone_discount_total,
        after_standalone=after_standalone,
        overall_discount_amount=overall_discount_amount,
        after_overall_discount=after_overall_discount,
        per_item_vat_total=per_item_vat_total,
        per_item_wht_total=per_item_wht_total,
        overall_vat_amount=overall_vat,
        overall_wht_amount=overall_wht,
        total_vat=total_vat,
        total_wht=total_wht,
        grand_total=grand_total,
    )
