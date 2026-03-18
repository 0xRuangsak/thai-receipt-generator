from __future__ import annotations

import random
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from itertools import combinations_with_replacement, product
from typing import Iterator

from .models import (
    Discount,
    DiscountType,
    LineItem,
    ReceiptConfig,
    StandaloneDiscount,
)

TWO_PLACES = Decimal("0.01")


def _round(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


# Thai product/service names with realistic prices
SAMPLE_PRODUCTS: list[tuple[str, Decimal, bool]] = [
    # (name, unit_price, is_service)
    ("ไก่ทอด 3 ชิ้น", Decimal("89.00"), False),
    ("ข้าวผัดกุ้ง", Decimal("65.00"), False),
    ("น้ำส้ม", Decimal("25.00"), False),
    ("กาแฟเย็น", Decimal("45.00"), False),
    ("ปากกา 12 แท่ง", Decimal("120.00"), False),
    ("ค่าออกแบบโลโก้", Decimal("5000.00"), True),
    ("ค่าที่ปรึกษาธุรกิจ", Decimal("10000.00"), True),
    ("บริการซ่อมแอร์", Decimal("1500.00"), True),
    ("ค่าบริการขนส่ง", Decimal("350.00"), True),
    ("สมุด A4 5 เล่ม", Decimal("75.00"), False),
]

SAMPLE_STANDALONE_DISCOUNTS: list[tuple[str, Decimal]] = [
    ("ส่วนลด", Decimal("50.00")),
    ("ส่วนลดพิเศษ", Decimal("100.00")),
    ("ส่วนลดลูกค้าใหม่", Decimal("200.00")),
    ("ส่วนลดไก่ทอด", Decimal("20.00")),
    ("คูปองส่วนลด", Decimal("150.00")),
]


@dataclass(frozen=True)
class ItemProfile:
    has_vat: bool
    has_wht: bool
    discount_type: DiscountType


@dataclass
class CombinatorSpec:
    item_counts: list[int] = field(default_factory=lambda: [1, 2, 3])

    per_item_vat_options: list[bool] = field(default_factory=lambda: [False, True])
    per_item_wht_options: list[bool] = field(default_factory=lambda: [False, True])
    per_item_discount_options: list[DiscountType] = field(
        default_factory=lambda: [DiscountType.NONE, DiscountType.ABSOLUTE, DiscountType.PERCENTAGE]
    )

    standalone_discount_counts: list[int] = field(default_factory=lambda: [0, 1])
    overall_discount_options: list[DiscountType] = field(
        default_factory=lambda: [DiscountType.NONE, DiscountType.ABSOLUTE, DiscountType.PERCENTAGE]
    )
    overall_vat_options: list[bool] = field(default_factory=lambda: [False, True])
    overall_wht_options: list[bool] = field(default_factory=lambda: [False, True])

    template_names: list[str] = field(
        default_factory=lambda: ["formal_invoice", "simple_receipt", "thermal_pos"]
    )

    max_combinations: int | None = None
    seed: int = 42


def _build_profiles(spec: CombinatorSpec) -> list[ItemProfile]:
    return [
        ItemProfile(vat, wht, disc)
        for vat, wht, disc in product(
            spec.per_item_vat_options,
            spec.per_item_wht_options,
            spec.per_item_discount_options,
        )
    ]


def _make_discount(
    disc_type: DiscountType, rng: random.Random, max_absolute: Decimal | None = None
) -> Discount:
    if disc_type == DiscountType.NONE:
        return Discount()
    if disc_type == DiscountType.ABSOLUTE:
        choices = [Decimal("10"), Decimal("20"), Decimal("50"), Decimal("100")]
        if max_absolute is not None:
            choices = [c for c in choices if c <= max_absolute] or [_round(max_absolute * Decimal("0.1"))]
        return Discount(type=disc_type, value=rng.choice(choices))
    # percentage
    return Discount(type=disc_type, value=Decimal(str(rng.choice([5, 10, 15, 20]))))


def _make_line_item(
    profile: ItemProfile, product_pool: list[tuple[str, Decimal, bool]], idx: int, rng: random.Random
) -> LineItem:
    name, price, _is_service = product_pool[idx % len(product_pool)]
    qty = rng.choice([1, 2, 3])
    gross = price * qty
    return LineItem(
        name=name,
        quantity=qty,
        unit_price=price,
        has_vat=profile.has_vat,
        has_wht=profile.has_wht,
        wht_rate=Decimal(str(rng.choice([1, 2, 3, 5]))),
        discount=_make_discount(profile.discount_type, rng, max_absolute=gross),
    )


def _profile_code(p: ItemProfile) -> str:
    v = "vat1" if p.has_vat else "vat0"
    w = "wht1" if p.has_wht else "wht0"
    d = {"none": "dn", "absolute": "da", "percentage": "dp"}[p.discount_type.value]
    return f"{v}_{w}_{d}"


def _variation_id(
    item_count: int,
    profile_combo: tuple[ItemProfile, ...],
    sd_count: int,
    overall_disc: DiscountType,
    overall_vat: bool,
    overall_wht: bool,
    template: str,
) -> str:
    items_code = "-".join(_profile_code(p) for p in profile_combo)
    od = {"none": "odn", "absolute": "oda", "percentage": "odp"}[overall_disc.value]
    ov = "ovat1" if overall_vat else "ovat0"
    ow = "owht1" if overall_wht else "owht0"
    return f"i{item_count}_{items_code}_sd{sd_count}_{od}_{ov}_{ow}_{template}"


def generate(spec: CombinatorSpec) -> Iterator[ReceiptConfig]:
    rng = random.Random(spec.seed)
    profiles = _build_profiles(spec)

    all_combos: list[tuple] = []

    for item_count in spec.item_counts:
        profile_combos = list(combinations_with_replacement(profiles, item_count))

        for profile_combo, sd_count, overall_disc, overall_vat, overall_wht, template in product(
            profile_combos,
            spec.standalone_discount_counts,
            spec.overall_discount_options,
            spec.overall_vat_options,
            spec.overall_wht_options,
            spec.template_names,
        ):
            # Constraint: no per-item VAT if overall VAT is on (avoid double tax)
            if overall_vat and any(p.has_vat for p in profile_combo):
                continue
            if overall_wht and any(p.has_wht for p in profile_combo):
                continue

            all_combos.append(
                (item_count, profile_combo, sd_count, overall_disc, overall_vat, overall_wht, template)
            )

    if spec.max_combinations is not None and len(all_combos) > spec.max_combinations:
        all_combos = rng.sample(all_combos, spec.max_combinations)

    for item_count, profile_combo, sd_count, overall_disc, overall_vat, overall_wht, template in all_combos:
        items = [
            _make_line_item(profile_combo[i], SAMPLE_PRODUCTS, i, rng)
            for i in range(item_count)
        ]

        standalone_discounts = []
        for j in range(sd_count):
            name, amount = SAMPLE_STANDALONE_DISCOUNTS[j % len(SAMPLE_STANDALONE_DISCOUNTS)]
            standalone_discounts.append(StandaloneDiscount(name=name, amount=amount))

        yield ReceiptConfig(
            items=items,
            standalone_discounts=standalone_discounts,
            overall_discount=_make_discount(overall_disc, rng),
            overall_vat=overall_vat,
            overall_vat_rate=Decimal("7"),
            overall_wht=overall_wht,
            overall_wht_rate=Decimal("3"),
            template_name=template,
            variation_id=_variation_id(
                item_count, profile_combo, sd_count, overall_disc,
                overall_vat, overall_wht, template,
            ),
        )


def count_combinations(spec: CombinatorSpec) -> int:
    """Dry-run: count how many combos without generating configs."""
    profiles = _build_profiles(spec)
    total = 0

    for item_count in spec.item_counts:
        profile_combos = list(combinations_with_replacement(profiles, item_count))

        for profile_combo, _sd, overall_disc, overall_vat, overall_wht, _tmpl in product(
            profile_combos,
            spec.standalone_discount_counts,
            spec.overall_discount_options,
            spec.overall_vat_options,
            spec.overall_wht_options,
            spec.template_names,
        ):
            if overall_vat and any(p.has_vat for p in profile_combo):
                continue
            if overall_wht and any(p.has_wht for p in profile_combo):
                continue
            total += 1

    if spec.max_combinations is not None:
        return min(total, spec.max_combinations)
    return total
