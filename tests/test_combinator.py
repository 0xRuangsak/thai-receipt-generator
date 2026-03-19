from thai_receipt_generator.combinator import CombinatorSpec, TaxMode, count_combinations, generate
from thai_receipt_generator.models import DiscountType, VatStyle


def test_minimal_spec():
    spec = CombinatorSpec(
        item_counts=[1],
        vat_modes=[TaxMode(False, False)],
        vat_style_options=[VatStyle.EXCLUSIVE],
        wht_modes=[TaxMode(False, False)],
        per_item_discount_options=[DiscountType.NONE],
        standalone_discount_counts=[0],
        overall_discount_options=[DiscountType.NONE],
        template_names=["formal_invoice"],
    )
    assert count_combinations(spec) == 1
    configs = list(generate(spec))
    assert len(configs) == 1
    assert len(configs[0].items) == 1


def test_no_double_vat_in_tax_modes():
    """TaxMode ensures per_item and overall are never both True."""
    spec = CombinatorSpec(
        item_counts=[1],
        vat_modes=[TaxMode(True, False), TaxMode(False, True)],
        vat_style_options=[VatStyle.EXCLUSIVE],
        wht_modes=[TaxMode(False, False)],
        per_item_discount_options=[DiscountType.NONE],
        standalone_discount_counts=[0],
        overall_discount_options=[DiscountType.NONE],
        template_names=["formal_invoice"],
    )
    # 2 VAT modes * 1 WHT mode * 1 discount * 1 sd * 1 od * 1 tmpl = 2
    assert count_combinations(spec) == 2
    configs = list(generate(spec))
    # One has per-item VAT, other has overall VAT — never both
    vat_configs = [(c.items[0].has_vat, c.overall_vat) for c in configs]
    assert (True, False) in vat_configs
    assert (False, True) in vat_configs
    assert (True, True) not in vat_configs


def test_vat_style_skipped_when_vat_off():
    """When VAT is off, vat_style variation is irrelevant and skipped."""
    spec = CombinatorSpec(
        item_counts=[1],
        vat_modes=[TaxMode(False, False)],
        vat_style_options=[VatStyle.EXCLUSIVE, VatStyle.INCLUSIVE],
        wht_modes=[TaxMode(False, False)],
        per_item_discount_options=[DiscountType.NONE],
        standalone_discount_counts=[0],
        overall_discount_options=[DiscountType.NONE],
        template_names=["formal_invoice"],
    )
    # Only 1 combo — INCLUSIVE is skipped when VAT is off
    assert count_combinations(spec) == 1
    configs = list(generate(spec))
    assert len(configs) == 1


def test_vat_style_doubles_when_vat_on():
    """When VAT is on, both inclusive/exclusive generate separate configs."""
    spec = CombinatorSpec(
        item_counts=[1],
        vat_modes=[TaxMode(True, False)],
        vat_style_options=[VatStyle.EXCLUSIVE, VatStyle.INCLUSIVE],
        wht_modes=[TaxMode(False, False)],
        per_item_discount_options=[DiscountType.NONE],
        standalone_discount_counts=[0],
        overall_discount_options=[DiscountType.NONE],
        template_names=["formal_invoice"],
    )
    assert count_combinations(spec) == 2
    configs = list(generate(spec))
    styles = [c.vat_style for c in configs]
    assert VatStyle.EXCLUSIVE in styles
    assert VatStyle.INCLUSIVE in styles


def test_max_combinations_sampling():
    spec = CombinatorSpec(
        item_counts=[1, 2],
        max_combinations=5,
    )
    total_without_limit = count_combinations(CombinatorSpec(item_counts=[1, 2]))
    assert total_without_limit > 5
    assert count_combinations(spec) == 5

    configs = list(generate(spec))
    assert len(configs) == 5


def test_variation_ids_unique():
    spec = CombinatorSpec(
        item_counts=[1],
        vat_modes=[TaxMode(False, False), TaxMode(True, False), TaxMode(False, True)],
        vat_style_options=[VatStyle.EXCLUSIVE, VatStyle.INCLUSIVE],
        wht_modes=[TaxMode(False, False)],
        per_item_discount_options=[DiscountType.NONE],
        standalone_discount_counts=[0],
        overall_discount_options=[DiscountType.NONE],
        template_names=["formal_invoice"],
    )
    configs = list(generate(spec))
    ids = [c.variation_id for c in configs]
    # VAT off: 1 (only EXCLUSIVE) + per_item: 2 + overall: 2 = 5
    assert len(ids) == 5
    assert len(ids) == len(set(ids))
