from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import click
from dotenv import load_dotenv

from .calculator import calculate
from .combinator import CombinatorSpec, TaxMode, count_combinations, generate
from .models import (
    Discount,
    DiscountType,
    ItemType,
    LineItem,
    ReceiptConfig,
    StandaloneDiscount,
)
from .renderer import render_batch

load_dotenv()


# ── Serialization helpers ─────────────────────────────────────────────────────


def _discount_to_dict(d: Discount) -> dict | None:
    if d.type == DiscountType.NONE:
        return None
    return {"type": d.type.value, "value": float(d.value)}


def _config_to_dict(cfg: ReceiptConfig) -> dict:
    data: dict = {"template": cfg.template_name, "items": []}

    for item in cfg.items:
        entry: dict = {
            "name": item.name,
            "type": item.item_type.value,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
        }
        if item.has_vat:
            entry["has_vat"] = True
        if item.has_wht:
            entry["has_wht"] = True
            entry["wht_rate"] = float(item.wht_rate)
        disc = _discount_to_dict(item.discount)
        if disc:
            entry["discount"] = disc
        data["items"].append(entry)

    if cfg.standalone_discounts:
        data["standalone_discounts"] = []
        for sd in cfg.standalone_discounts:
            entry = {"name": sd.name, "amount": float(sd.amount)}
            if sd.position >= 0:
                entry["position"] = sd.position
            data["standalone_discounts"].append(entry)

    od = _discount_to_dict(cfg.overall_discount)
    if od:
        data["overall_discount"] = od
    if cfg.overall_vat:
        data["overall_vat"] = True
        if cfg.overall_vat_rate != Decimal("7"):
            data["overall_vat_rate"] = float(cfg.overall_vat_rate)
    if cfg.overall_wht:
        data["overall_wht"] = True
        if cfg.overall_wht_rate != Decimal("3"):
            data["overall_wht_rate"] = float(cfg.overall_wht_rate)

    return data


def _parse_discount(d: dict | None) -> Discount:
    if not d:
        return Discount()
    return Discount(
        type=DiscountType(d.get("type", "none")),
        value=Decimal(str(d.get("value", 0))),
    )


def _parse_config(data: dict) -> ReceiptConfig:
    items = []
    for item in data.get("items", []):
        items.append(LineItem(
            name=item["name"],
            item_type=ItemType(item.get("type", "product")),
            quantity=item.get("quantity", 1),
            unit_price=Decimal(str(item["unit_price"])),
            has_vat=item.get("has_vat", False),
            has_wht=item.get("has_wht", False),
            wht_rate=Decimal(str(item.get("wht_rate", 3))),
            discount=_parse_discount(item.get("discount")),
        ))

    standalone_discounts = []
    for sd in data.get("standalone_discounts", []):
        standalone_discounts.append(StandaloneDiscount(
            name=sd.get("name", "ส่วนลด"),
            amount=Decimal(str(sd["amount"])),
            position=sd.get("position", -1),
        ))

    return ReceiptConfig(
        items=items,
        standalone_discounts=standalone_discounts,
        overall_discount=_parse_discount(data.get("overall_discount")),
        overall_vat=data.get("overall_vat", False),
        overall_vat_rate=Decimal(str(data.get("overall_vat_rate", 7))),
        overall_wht=data.get("overall_wht", False),
        overall_wht_rate=Decimal(str(data.get("overall_wht_rate", 3))),
        template_name=data.get("template", "formal_invoice"),
    )


# ── Spec builder ──────────────────────────────────────────────────────────────


_TAX_CHOICES = click.Choice(["none", "per_item", "overall", "vary"])
_DISCOUNT_CHOICES = click.Choice(["true", "false", "vary"])


def _tax_modes(val: str) -> list[TaxMode]:
    """Convert tax setting to list of valid TaxMode combos."""
    if val == "none":
        return [TaxMode(False, False)]
    if val == "per_item":
        return [TaxMode(True, False)]
    if val == "overall":
        return [TaxMode(False, True)]
    # vary: all 3 valid combos (never both True)
    return [TaxMode(False, False), TaxMode(True, False), TaxMode(False, True)]


def _discount_axis(val: str) -> list[DiscountType]:
    if val == "true":
        return [DiscountType.ABSOLUTE, DiscountType.PERCENTAGE]
    if val == "false":
        return [DiscountType.NONE]
    return [DiscountType.NONE, DiscountType.ABSOLUTE, DiscountType.PERCENTAGE]


def _standalone_axis(val: str) -> list[int]:
    if val == "true":
        return [1]
    if val == "false":
        return [0]
    return [0, 1]


def _build_spec(
    items: str,
    tmpl_formal_invoice: bool,
    tmpl_simple_receipt: bool,
    tmpl_thermal_pos: bool,
    max_combos: int | None,
    seed: int,
    vat: str,
    wht: str,
    per_item_discount: str,
    standalone_discount: str,
    overall_discount: str,
) -> CombinatorSpec:
    templates = []
    if tmpl_formal_invoice:
        templates.append("formal_invoice")
    if tmpl_simple_receipt:
        templates.append("simple_receipt")
    if tmpl_thermal_pos:
        templates.append("thermal_pos")
    if not templates:
        templates = ["formal_invoice"]

    return CombinatorSpec(
        item_counts=[int(x) for x in items.split(",")],
        vat_modes=_tax_modes(vat),
        wht_modes=_tax_modes(wht),
        per_item_discount_options=_discount_axis(per_item_discount),
        standalone_discount_counts=_standalone_axis(standalone_discount),
        overall_discount_options=_discount_axis(overall_discount),
        template_names=templates,
        max_combinations=max_combos,
        seed=seed,
    )


# Shared options for combinator commands
_shared_options = [
    click.option("--items", envvar="RECEIPT_ITEMS", default="1,2,3", help="Comma-separated item counts"),
    click.option("--tmpl-formal-invoice/--no-tmpl-formal-invoice", envvar="RECEIPT_TMPL_FORMAL_INVOICE", default=True, help="Include formal invoice template"),
    click.option("--tmpl-simple-receipt/--no-tmpl-simple-receipt", envvar="RECEIPT_TMPL_SIMPLE_RECEIPT", default=True, help="Include simple receipt template"),
    click.option("--tmpl-thermal-pos/--no-tmpl-thermal-pos", envvar="RECEIPT_TMPL_THERMAL_POS", default=True, help="Include thermal POS template"),
    click.option("--max-combos", envvar="RECEIPT_MAX_COMBOS", default=None, type=int, help="Max combinations to sample"),
    click.option("--seed", envvar="RECEIPT_SEED", default=42, type=int, help="Random seed"),
    click.option("--vat", envvar="RECEIPT_VAT", type=_TAX_CHOICES, default="vary", help="VAT mode: none/per_item/overall/vary"),
    click.option("--wht", envvar="RECEIPT_WHT", type=_TAX_CHOICES, default="vary", help="WHT mode: none/per_item/overall/vary"),
    click.option("--per-item-discount", envvar="RECEIPT_PER_ITEM_DISCOUNT", type=_DISCOUNT_CHOICES, default="vary", help="Per-item discount: true/false/vary"),
    click.option("--standalone-discount", envvar="RECEIPT_STANDALONE_DISCOUNT", type=_DISCOUNT_CHOICES, default="vary", help="Standalone discount rows: true/false/vary"),
    click.option("--overall-discount", envvar="RECEIPT_OVERALL_DISCOUNT", type=_DISCOUNT_CHOICES, default="vary", help="Overall discount: true/false/vary"),
]


def _add_shared_options(func):
    for option in reversed(_shared_options):
        func = option(func)
    return func


# ── CLI Commands ──────────────────────────────────────────────────────────────


@click.group()
def main() -> None:
    """Thai Receipt Generator — generate varied receipt images for OCR testing."""
    pass


@main.command("gen-json")
@click.option("--json-dir", envvar="RECEIPT_JSON_DIR", default="generated_json", type=click.Path(), help="Output directory for JSON files")
@_add_shared_options
def gen_json(
    json_dir: str,
    items: str,
    tmpl_formal_invoice: bool,
    tmpl_simple_receipt: bool,
    tmpl_thermal_pos: bool,
    max_combos: int | None,
    seed: int,
    vat: str,
    wht: str,
    per_item_discount: str,
    standalone_discount: str,
    overall_discount: str,
) -> None:
    """Step 1: Generate JSON configs from combinatorial spec. Review/edit them before rendering."""
    spec = _build_spec(
        items, tmpl_formal_invoice, tmpl_simple_receipt, tmpl_thermal_pos,
        max_combos, seed,
        vat, wht, per_item_discount,
        standalone_discount, overall_discount,
    )

    total = count_combinations(spec)
    click.echo(f"Generating {total} JSON configs...")

    out = Path(json_dir)
    out.mkdir(parents=True, exist_ok=True)

    count = 0
    for cfg in generate(spec):
        data = _config_to_dict(cfg)
        filename = cfg.variation_id or f"receipt_{count:04d}"
        path = out / f"{filename}.json"
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        count += 1

    click.echo(f"Done! {count} JSON files saved to {out.resolve()}")
    click.echo(f"Review/edit them, then run: thai-receipt-gen render {json_dir}")


@main.command()
@click.argument("json_dir", type=click.Path(exists=True))
@click.option("--output-dir", "-o", envvar="RECEIPT_OUTPUT_DIR", default="output", type=click.Path(), help="Output directory for PNGs")
@click.option("--dpi", envvar="RECEIPT_DPI", default=150, type=int, help="Rendering DPI")
def render(json_dir: str, output_dir: str, dpi: int) -> None:
    """Step 2: Render all JSON configs in a directory to PNG images."""
    json_path = Path(json_dir)
    json_files = sorted(json_path.glob("*.json"))

    if not json_files:
        click.echo(f"No JSON files found in {json_path}")
        return

    click.echo(f"Rendering {len(json_files)} receipts...")

    receipts = []
    for jf in json_files:
        data = json.loads(jf.read_text(encoding="utf-8"))
        config = _parse_config(data)
        config.variation_id = jf.stem
        receipts.append(calculate(config))

    out = Path(output_dir)
    paths = render_batch(receipts, out, dpi=dpi)

    click.echo(f"Done! {len(paths)} images saved to {out.resolve()}")


@main.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option("--output", "-o", envvar="RECEIPT_OUTPUT_DIR", default="output", help="Output file or directory")
@click.option("--dpi", envvar="RECEIPT_DPI", default=150, type=int, help="Rendering DPI")
def single(config_file: str, output: str, dpi: int) -> None:
    """Render a single JSON config file to a PNG image."""
    data = json.loads(Path(config_file).read_text(encoding="utf-8"))
    config = _parse_config(data)
    receipt = calculate(config)

    out = Path(output)
    if out.suffix == ".png":
        out_dir = out.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        paths = render_batch([receipt], out_dir, dpi=dpi)
        paths[0].rename(out)
        click.echo(f"Saved → {out}")
    else:
        paths = render_batch([receipt], out, dpi=dpi)
        click.echo(f"Saved → {paths[0]}")


@main.command("list-combos")
@_add_shared_options
def list_combos(
    items: str,
    tmpl_formal_invoice: bool,
    tmpl_simple_receipt: bool,
    tmpl_thermal_pos: bool,
    max_combos: int | None,
    seed: int,
    vat: str,
    wht: str,
    per_item_discount: str,
    standalone_discount: str,
    overall_discount: str,
) -> None:
    """Dry run: count combinations without rendering."""
    spec = _build_spec(
        items, tmpl_formal_invoice, tmpl_simple_receipt, tmpl_thermal_pos,
        max_combos, seed,
        vat, wht, per_item_discount,
        standalone_discount, overall_discount,
    )
    total = count_combinations(spec)
    click.echo(f"Total combinations: {total}")


if __name__ == "__main__":
    main()
