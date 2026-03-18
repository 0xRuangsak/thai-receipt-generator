from thai_receipt_generator.combinator import CombinatorSpec, TaxMode, count_combinations, generate
from thai_receipt_generator.models import DiscountType


def test_minimal_spec():
    spec = CombinatorSpec(
        item_counts=[1],
        vat_modes=[TaxMode(False, False)],
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
        wht_modes=[TaxMode(False, False)],
        per_item_discount_options=[DiscountType.NONE],
        standalone_discount_counts=[0],
        overall_discount_options=[DiscountType.NONE],
        template_names=["formal_invoice"],
    )
    configs = list(generate(spec))
    ids = [c.variation_id for c in configs]
    assert len(ids) == len(set(ids))
