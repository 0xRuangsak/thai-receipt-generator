from decimal import Decimal

from thai_receipt_generator.calculator import calculate
from thai_receipt_generator.models import (
    Discount,
    DiscountType,
    LineItem,
    ReceiptConfig,
    StandaloneDiscount,
)


def test_simple_single_item():
    cfg = ReceiptConfig(items=[
        LineItem(name="ไก่ทอด", quantity=2, unit_price=Decimal("89.00")),
    ])
    r = calculate(cfg)
    assert r.subtotal == Decimal("178.00")
    assert r.grand_total == Decimal("178.00")
    assert r.total_vat == Decimal("0")
    assert r.total_wht == Decimal("0")


def test_item_with_absolute_discount():
    cfg = ReceiptConfig(items=[
        LineItem(
            name="ไก่ทอด", quantity=1, unit_price=Decimal("100.00"),
            discount=Discount(type=DiscountType.ABSOLUTE, value=Decimal("20")),
        ),
    ])
    r = calculate(cfg)
    assert r.calculated_items[0].gross_amount == Decimal("100.00")
    assert r.calculated_items[0].discount_amount == Decimal("20.00")
    assert r.calculated_items[0].net_amount == Decimal("80.00")
    assert r.grand_total == Decimal("80.00")


def test_item_with_percentage_discount():
    cfg = ReceiptConfig(items=[
        LineItem(
            name="กาแฟ", quantity=1, unit_price=Decimal("200.00"),
            discount=Discount(type=DiscountType.PERCENTAGE, value=Decimal("10")),
        ),
    ])
    r = calculate(cfg)
    assert r.calculated_items[0].discount_amount == Decimal("20.00")
    assert r.calculated_items[0].net_amount == Decimal("180.00")


def test_per_item_vat():
    cfg = ReceiptConfig(items=[
        LineItem(name="ไก่ทอด", quantity=1, unit_price=Decimal("100.00"), has_vat=True),
    ])
    r = calculate(cfg)
    assert r.calculated_items[0].vat_amount == Decimal("7.00")
    assert r.total_vat == Decimal("7.00")
    assert r.grand_total == Decimal("107.00")


def test_per_item_wht():
    cfg = ReceiptConfig(items=[
        LineItem(
            name="ค่าที่ปรึกษา", quantity=1, unit_price=Decimal("10000.00"),
            has_wht=True, wht_rate=Decimal("3"),
        ),
    ])
    r = calculate(cfg)
    assert r.calculated_items[0].wht_amount == Decimal("300.00")
    assert r.total_wht == Decimal("300.00")
    assert r.grand_total == Decimal("9700.00")


def test_standalone_discount():
    cfg = ReceiptConfig(
        items=[LineItem(name="ไก่ทอด", quantity=1, unit_price=Decimal("500.00"))],
        standalone_discounts=[StandaloneDiscount(name="ส่วนลด", amount=Decimal("50.00"))],
    )
    r = calculate(cfg)
    assert r.subtotal == Decimal("500.00")
    assert r.standalone_discount_total == Decimal("50.00")
    assert r.after_standalone == Decimal("450.00")
    assert r.grand_total == Decimal("450.00")


def test_overall_vat():
    cfg = ReceiptConfig(
        items=[LineItem(name="ไก่ทอด", quantity=1, unit_price=Decimal("1000.00"))],
        overall_vat=True,
        overall_vat_rate=Decimal("7"),
    )
    r = calculate(cfg)
    assert r.overall_vat_amount == Decimal("70.00")
    assert r.grand_total == Decimal("1070.00")


def test_overall_wht():
    cfg = ReceiptConfig(
        items=[LineItem(name="ค่าที่ปรึกษา", quantity=1, unit_price=Decimal("10000.00"))],
        overall_wht=True,
        overall_wht_rate=Decimal("3"),
    )
    r = calculate(cfg)
    assert r.overall_wht_amount == Decimal("300.00")
    assert r.grand_total == Decimal("9700.00")


def test_overall_percentage_discount():
    cfg = ReceiptConfig(
        items=[LineItem(name="ไก่ทอด", quantity=1, unit_price=Decimal("1000.00"))],
        overall_discount=Discount(type=DiscountType.PERCENTAGE, value=Decimal("10")),
    )
    r = calculate(cfg)
    assert r.overall_discount_amount == Decimal("100.00")
    assert r.grand_total == Decimal("900.00")


def test_full_scenario_like_sample_code():
    """Reproduces the scenario from the user's sample code."""
    cfg = ReceiptConfig(
        items=[
            LineItem(name="ค่าออกแบบโลโก้", quantity=1, unit_price=Decimal("5000.00")),
            LineItem(
                name="ค่าที่ปรึกษาธุรกิจ", quantity=1, unit_price=Decimal("10000.00"),
                has_wht=True, wht_rate=Decimal("3"),
            ),
        ],
        standalone_discounts=[
            StandaloneDiscount(name="ส่วนลด", amount=Decimal("500.00")),
        ],
        overall_vat=True,
        overall_vat_rate=Decimal("7"),
    )
    r = calculate(cfg)

    assert r.subtotal == Decimal("15000.00")
    assert r.standalone_discount_total == Decimal("500.00")
    assert r.after_standalone == Decimal("14500.00")
    assert r.overall_vat_amount == Decimal("1015.00")
    assert r.per_item_wht_total == Decimal("300.00")
    assert r.grand_total == Decimal("15215.00")
