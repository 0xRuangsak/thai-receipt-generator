from thai_receipt_generator.combinator import CombinatorSpec, count_combinations, generate
from thai_receipt_generator.models import DiscountType


def test_minimal_spec():
    spec = CombinatorSpec(
        item_counts=[1],
        per_item_vat_options=[False],
        per_item_wht_options=[False],
        per_item_discount_options=[DiscountType.NONE],
        standalone_discount_counts=[0],
        overall_discount_options=[DiscountType.NONE],
        overall_vat_options=[False],
        overall_wht_options=[False],
        template_names=["formal_invoice"],
    )
    assert count_combinations(spec) == 1
    configs = list(generate(spec))
    assert len(configs) == 1
    assert len(configs[0].items) == 1


def test_constraint_filters_double_vat():
    """Overall VAT + per-item VAT combos should be filtered out."""
    spec = CombinatorSpec(
        item_counts=[1],
        per_item_vat_options=[True],
        per_item_wht_options=[False],
        per_item_discount_options=[DiscountType.NONE],
        standalone_discount_counts=[0],
        overall_discount_options=[DiscountType.NONE],
        overall_vat_options=[True],
        overall_wht_options=[False],
        template_names=["formal_invoice"],
    )
    # All items have VAT and overall VAT is on → all filtered out
    assert count_combinations(spec) == 0


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
        per_item_vat_options=[False, True],
        per_item_wht_options=[False],
        per_item_discount_options=[DiscountType.NONE],
        standalone_discount_counts=[0],
        overall_discount_options=[DiscountType.NONE],
        overall_vat_options=[False],
        overall_wht_options=[False],
        template_names=["formal_invoice"],
    )
    configs = list(generate(spec))
    ids = [c.variation_id for c in configs]
    assert len(ids) == len(set(ids))
