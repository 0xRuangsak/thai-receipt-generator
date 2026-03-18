from __future__ import annotations

from pathlib import Path

import click
from dotenv import load_dotenv

from .calculator import calculate
from .combinator import CombinatorSpec, count_combinations, generate
from .models import DiscountType
from .renderer import render_batch

load_dotenv()


def _build_spec(
    items: str,
    templates: str,
    max_combos: int | None,
    seed: int,
    no_per_item_vat: bool,
    no_per_item_wht: bool,
    no_per_item_discount: bool,
    no_standalone_discount: bool,
    no_overall_discount: bool,
    no_overall_vat: bool,
    no_overall_wht: bool,
) -> CombinatorSpec:
    return CombinatorSpec(
        item_counts=[int(x) for x in items.split(",")],
        per_item_vat_options=[False] if no_per_item_vat else [False, True],
        per_item_wht_options=[False] if no_per_item_wht else [False, True],
        per_item_discount_options=(
            [DiscountType.NONE] if no_per_item_discount
            else [DiscountType.NONE, DiscountType.ABSOLUTE, DiscountType.PERCENTAGE]
        ),
        standalone_discount_counts=[0] if no_standalone_discount else [0, 1],
        overall_discount_options=(
            [DiscountType.NONE] if no_overall_discount
            else [DiscountType.NONE, DiscountType.ABSOLUTE, DiscountType.PERCENTAGE]
        ),
        overall_vat_options=[False] if no_overall_vat else [False, True],
        overall_wht_options=[False] if no_overall_wht else [False, True],
        template_names=[t.strip() for t in templates.split(",")],
        max_combinations=max_combos,
        seed=seed,
    )


# Shared options for both commands
_shared_options = [
    click.option("--items", envvar="RECEIPT_ITEMS", default="1,2,3", help="Comma-separated item counts"),
    click.option("--templates", envvar="RECEIPT_TEMPLATES", default="formal_invoice,simple_receipt,thermal_pos", help="Comma-separated template names"),
    click.option("--max-combos", envvar="RECEIPT_MAX_COMBOS", default=None, type=int, help="Max combinations to sample"),
    click.option("--seed", envvar="RECEIPT_SEED", default=42, type=int, help="Random seed"),
    click.option("--no-per-item-vat", envvar="RECEIPT_NO_PER_ITEM_VAT", is_flag=True, help="Disable per-item VAT axis"),
    click.option("--no-per-item-wht", envvar="RECEIPT_NO_PER_ITEM_WHT", is_flag=True, help="Disable per-item WHT axis"),
    click.option("--no-per-item-discount", envvar="RECEIPT_NO_PER_ITEM_DISCOUNT", is_flag=True, help="Disable per-item discount axis"),
    click.option("--no-standalone-discount", envvar="RECEIPT_NO_STANDALONE_DISCOUNT", is_flag=True, help="Disable standalone discount axis"),
    click.option("--no-overall-discount", envvar="RECEIPT_NO_OVERALL_DISCOUNT", is_flag=True, help="Disable overall discount axis"),
    click.option("--no-overall-vat", envvar="RECEIPT_NO_OVERALL_VAT", is_flag=True, help="Disable overall VAT axis"),
    click.option("--no-overall-wht", envvar="RECEIPT_NO_OVERALL_WHT", is_flag=True, help="Disable overall WHT axis"),
]


def _add_shared_options(func):
    for option in reversed(_shared_options):
        func = option(func)
    return func


@click.group()
def main() -> None:
    """Thai Receipt Generator — generate varied receipt images for OCR testing."""
    pass


@main.command()
@click.option("--output-dir", envvar="RECEIPT_OUTPUT_DIR", default="output", type=click.Path(), help="Output directory")
@click.option("--dpi", envvar="RECEIPT_DPI", default=150, type=int, help="Rendering DPI")
@_add_shared_options
def gen(
    items: str,
    templates: str,
    max_combos: int | None,
    seed: int,
    output_dir: str,
    dpi: int,
    no_per_item_vat: bool,
    no_per_item_wht: bool,
    no_per_item_discount: bool,
    no_standalone_discount: bool,
    no_overall_discount: bool,
    no_overall_vat: bool,
    no_overall_wht: bool,
) -> None:
    """Generate receipt images from combinatorial spec."""
    spec = _build_spec(
        items, templates, max_combos, seed,
        no_per_item_vat, no_per_item_wht, no_per_item_discount,
        no_standalone_discount, no_overall_discount, no_overall_vat, no_overall_wht,
    )

    total = count_combinations(spec)
    click.echo(f"Generating {total} receipt variations...")

    configs = list(generate(spec))
    receipts = [calculate(cfg) for cfg in configs]

    out = Path(output_dir)
    paths = render_batch(receipts, out, dpi=dpi)

    click.echo(f"Done! {len(paths)} images saved to {out.resolve()}")


@main.command("list-combos")
@_add_shared_options
def list_combos(
    items: str,
    templates: str,
    max_combos: int | None,
    seed: int,
    no_per_item_vat: bool,
    no_per_item_wht: bool,
    no_per_item_discount: bool,
    no_standalone_discount: bool,
    no_overall_discount: bool,
    no_overall_vat: bool,
    no_overall_wht: bool,
) -> None:
    """Dry run: count combinations without rendering."""
    spec = _build_spec(
        items, templates, max_combos, seed,
        no_per_item_vat, no_per_item_wht, no_per_item_discount,
        no_standalone_discount, no_overall_discount, no_overall_vat, no_overall_wht,
    )
    total = count_combinations(spec)
    click.echo(f"Total combinations: {total}")


if __name__ == "__main__":
    main()
