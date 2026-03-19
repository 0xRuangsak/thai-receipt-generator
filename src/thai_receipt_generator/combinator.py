from __future__ import annotations

import random
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from itertools import combinations_with_replacement, product
from typing import Iterator

from .models import (
    Discount,
    DiscountType,
    ItemType,
    LineItem,
    ReceiptConfig,
    StandaloneDiscount,
    VatStyle,
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



@dataclass(frozen=True)
class ItemProfile:
    has_vat: bool
    has_wht: bool
    discount_type: DiscountType


@dataclass(frozen=True)
class TaxMode:
    """A valid (per_item, overall) combination for VAT or WHT."""
    per_item: bool
    overall: bool


@dataclass
class CombinatorSpec:
    item_counts: list[int] = field(default_factory=lambda: [1, 2, 3])

    # VAT/WHT: list of valid (per_item, overall) combos — never both True
    vat_modes: list[TaxMode] = field(default_factory=lambda: [
        TaxMode(False, False), TaxMode(True, False), TaxMode(False, True),
    ])
    vat_style_options: list[VatStyle] = field(default_factory=lambda: [
        VatStyle.EXCLUSIVE, VatStyle.INCLUSIVE,
    ])
    wht_modes: list[TaxMode] = field(default_factory=lambda: [
        TaxMode(False, False), TaxMode(True, False), TaxMode(False, True),
    ])

    per_item_discount_options: list[DiscountType] = field(
        default_factory=lambda: [DiscountType.NONE, DiscountType.ABSOLUTE, DiscountType.PERCENTAGE]
    )
    standalone_discount_counts: list[int] = field(default_factory=lambda: [0, 1])
    overall_discount_options: list[DiscountType] = field(
        default_factory=lambda: [DiscountType.NONE, DiscountType.ABSOLUTE, DiscountType.PERCENTAGE]
    )

    template_names: list[str] = field(
        default_factory=lambda: ["formal_invoice", "simple_receipt", "thermal_pos"]
    )

    max_combinations: int | None = None
    seed: int = 42


def _build_discount_profiles(spec: CombinatorSpec) -> list[DiscountType]:
    """Get unique per-item discount options."""
    return spec.per_item_discount_options


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


SAMPLE_SERVICES = [(n, p) for n, p, s in SAMPLE_PRODUCTS if s]
SAMPLE_GOODS = [(n, p) for n, p, s in SAMPLE_PRODUCTS if not s]


def _make_line_item(
    profile: ItemProfile, idx: int, rng: random.Random, force_service: bool = False,
) -> LineItem:
    # WHT only applies to services — pick from the right pool
    is_service = profile.has_wht or force_service
    if is_service:
        pool = SAMPLE_SERVICES
    else:
        pool = SAMPLE_GOODS
    name, price = pool[idx % len(pool)]
    qty = rng.choice([1, 2, 3])
    gross = price * qty
    return LineItem(
        name=name,
        item_type=ItemType.SERVICE if is_service else ItemType.PRODUCT,
        quantity=qty,
        unit_price=price,
        has_vat=profile.has_vat,
        has_wht=profile.has_wht,
        wht_rate=Decimal(str(rng.choice([1, 2, 3, 5]))) if profile.has_wht else Decimal("3"),
        discount=_make_discount(profile.discount_type, rng, max_absolute=gross),
    )


def _profile_code(p: ItemProfile) -> str:
    v = "vat1" if p.has_vat else "vat0"
    w = "wht1" if p.has_wht else "wht0"
    d = {"none": "dn", "absolute": "da", "percentage": "dp"}[p.discount_type.value]
    return f"{v}_{w}_{d}"


def _tax_mode_code(mode: TaxMode, prefix: str) -> str:
    if mode.per_item:
        return f"{prefix}_pi"
    if mode.overall:
        return f"{prefix}_oa"
    return f"{prefix}_off"


def _vat_style_code(style: VatStyle) -> str:
    return "vinc" if style == VatStyle.INCLUSIVE else "vexc"


def _variation_id(
    item_count: int,
    profile_combo: tuple[ItemProfile, ...],
    sd_count: int,
    overall_disc: DiscountType,
    vat_mode: TaxMode,
    vat_style: VatStyle,
    wht_mode: TaxMode,
    template: str,
) -> str:
    items_code = "-".join(_profile_code(p) for p in profile_combo)
    od = {"none": "odn", "absolute": "oda", "percentage": "odp"}[overall_disc.value]
    vat_code = _tax_mode_code(vat_mode, "vat")
    vs_code = _vat_style_code(vat_style)
    wht_code = _tax_mode_code(wht_mode, "wht")
    return f"i{item_count}_{items_code}_sd{sd_count}_{od}_{vat_code}_{vs_code}_{wht_code}_{template}"


def generate(spec: CombinatorSpec) -> Iterator[ReceiptConfig]:
    rng = random.Random(spec.seed)
    discount_options = _build_discount_profiles(spec)

    all_combos: list[tuple] = []

    for item_count in spec.item_counts:
        # Per-item discount combos (each item gets a discount type independently)
        discount_combos = list(combinations_with_replacement(discount_options, item_count))

        for disc_combo, vat_mode, vat_style, wht_mode, sd_count, overall_disc, template in product(
            discount_combos,
            spec.vat_modes,
            spec.vat_style_options,
            spec.wht_modes,
            spec.standalone_discount_counts,
            spec.overall_discount_options,
            spec.template_names,
        ):
            # Skip vat_style variation when VAT is off — style is irrelevant
            if not vat_mode.per_item and not vat_mode.overall and vat_style != VatStyle.EXCLUSIVE:
                continue
            all_combos.append(
                (item_count, disc_combo, vat_mode, vat_style, wht_mode, sd_count, overall_disc, template)
            )

    if spec.max_combinations is not None and len(all_combos) > spec.max_combinations:
        all_combos = rng.sample(all_combos, spec.max_combinations)

    for item_count, disc_combo, vat_mode, vat_style, wht_mode, sd_count, overall_disc, template in all_combos:
        # Build item profiles from tax modes + discount combo
        profiles = [
            ItemProfile(
                has_vat=vat_mode.per_item,
                has_wht=wht_mode.per_item,
                discount_type=disc_combo[i],
            )
            for i in range(item_count)
        ]
        items = [
            _make_line_item(profiles[i], i, rng, force_service=wht_mode.overall)
            for i in range(item_count)
        ]

        standalone_discounts = []
        for _ in range(sd_count):
            # Always reference a specific item
            target_idx = rng.randrange(len(items))
            target = items[target_idx]
            name = f"ส่วนลด{target.name}"
            max_amt = target.unit_price
            position = rng.choice([target_idx + 1, -1])
            amount = Decimal(str(rng.choice([10, 20, 50, 100])))
            amount = min(amount, max_amt)
            standalone_discounts.append(StandaloneDiscount(name=name, amount=amount, position=position))

        vid = _variation_id(
            item_count, tuple(profiles), sd_count, overall_disc,
            vat_mode, vat_style, wht_mode, template,
        )

        yield ReceiptConfig(
            items=items,
            standalone_discounts=standalone_discounts,
            overall_discount=_make_discount(overall_disc, rng),
            overall_vat=vat_mode.overall,
            overall_vat_rate=Decimal("7"),
            vat_style=vat_style,
            overall_wht=wht_mode.overall,
            overall_wht_rate=Decimal("3"),
            template_name=template,
            variation_id=vid,
        )


def count_combinations(spec: CombinatorSpec) -> int:
    """Dry-run: count how many combos without generating configs."""
    discount_options = _build_discount_profiles(spec)
    total = 0

    for item_count in spec.item_counts:
        discount_combos = list(combinations_with_replacement(discount_options, item_count))

        for _dc, _vm, _vs, _wm, _sd, _od, _tmpl in product(
            discount_combos,
            spec.vat_modes,
            spec.vat_style_options,
            spec.wht_modes,
            spec.standalone_discount_counts,
            spec.overall_discount_options,
            spec.template_names,
        ):
            # Skip vat_style variation when VAT is off
            if not _vm.per_item and not _vm.overall and _vs != VatStyle.EXCLUSIVE:
                continue
            total += 1

    if spec.max_combinations is not None:
        return min(total, spec.max_combinations)
    return total
