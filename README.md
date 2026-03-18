# Thai Receipt Generator

Generate varied Thai receipt/invoice PNG images for OCR testing. Produces combinatorial variations across line-item features (VAT, WHT, discounts) and visual templates.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium

cp .env.example .env   # edit as needed
```

## Workflow

### Batch: generate variations

Two-step flow — generate JSONs first, review/edit, then render to PNGs.

```bash
# Step 1: Generate JSON configs
thai-receipt-gen gen-json

# Step 2: Review/edit JSONs in generated_json/, then render
thai-receipt-gen render generated_json
```

The JSONs are human-readable and editable — change item names, prices, discounts, or delete unwanted variations before rendering.

### Single: one receipt from JSON

Write your own JSON, get one PNG.

```bash
thai-receipt-gen single examples/simple.json -o output/my_receipt.png
```

## JSON Format

```json
{
  "template": "formal_invoice",
  "items": [
    {
      "name": "ไก่ทอด 3 ชิ้น",
      "quantity": 2,
      "unit_price": 89
    },
    {
      "name": "ค่าที่ปรึกษาธุรกิจ",
      "quantity": 1,
      "unit_price": 10000,
      "has_vat": true,
      "has_wht": true,
      "wht_rate": 3,
      "discount": { "type": "percentage", "value": 10 }
    }
  ],
  "standalone_discounts": [
    { "name": "ส่วนลดไก่ทอด", "amount": 20 }
  ],
  "overall_discount": { "type": "absolute", "value": 200 },
  "overall_vat": true
}
```

**Item fields:**

| Field | Required | Default | Description |
| --- | --- | --- | --- |
| `name` | yes | - | Thai item name |
| `quantity` | no | 1 | Quantity |
| `unit_price` | yes | - | Price per unit |
| `has_vat` | no | false | Per-item VAT 7% |
| `has_wht` | no | false | Per-item withholding tax |
| `wht_rate` | no | 3 | WHT percentage (1, 2, 3, or 5) |
| `discount` | no | none | `{"type": "absolute"/"percentage", "value": N}` |

**Receipt-level fields:**

| Field | Default | Description |
| --- | --- | --- |
| `template` | formal_invoice | Template name |
| `standalone_discounts` | [] | Absolute discount rows (generic or item-specific) |
| `overall_discount` | none | Discount on entire receipt |
| `overall_vat` | false | VAT 7% on entire receipt |
| `overall_wht` | false | WHT on entire receipt |

See `examples/` for ready-to-use JSON files.

## Configuration (.env)

All batch settings live in `.env`. CLI flags override `.env` values.

```bash
# ── General ──────────────────────────────────────
RECEIPT_JSON_DIR=generated_json
RECEIPT_OUTPUT_DIR=output
RECEIPT_DPI=150

# ── Batch generation ─────────────────────────────
RECEIPT_ITEMS=1,2,3
RECEIPT_TEMPLATES=formal_invoice,simple_receipt,thermal_pos
RECEIPT_MAX_COMBOS=50
RECEIPT_SEED=42

# ── Disable variation axes (set to true) ─────────
RECEIPT_NO_PER_ITEM_VAT=false
RECEIPT_NO_PER_ITEM_WHT=false
RECEIPT_NO_PER_ITEM_DISCOUNT=false
RECEIPT_NO_STANDALONE_DISCOUNT=false
RECEIPT_NO_OVERALL_DISCOUNT=false
RECEIPT_NO_OVERALL_VAT=false
RECEIPT_NO_OVERALL_WHT=false
```

## CLI Reference

| Command | Description |
| --- | --- |
| `thai-receipt-gen gen-json` | Step 1: generate JSON configs into `generated_json/` |
| `thai-receipt-gen render <dir>` | Step 2: render all JSONs in a directory to PNGs |
| `thai-receipt-gen single <file>` | Render one JSON to one PNG |
| `thai-receipt-gen list-combos` | Dry run: count combinations without generating |

## Variation Axes

| Axis | Options | Env var |
| --- | --- | --- |
| Per-item VAT | on / off | `RECEIPT_NO_PER_ITEM_VAT` |
| Per-item WHT | on / off | `RECEIPT_NO_PER_ITEM_WHT` |
| Per-item discount | none / absolute / % | `RECEIPT_NO_PER_ITEM_DISCOUNT` |
| Standalone discount rows | 0 / 1 | `RECEIPT_NO_STANDALONE_DISCOUNT` |
| Overall discount | none / absolute / % | `RECEIPT_NO_OVERALL_DISCOUNT` |
| Overall VAT | on / off | `RECEIPT_NO_OVERALL_VAT` |
| Overall WHT | on / off | `RECEIPT_NO_OVERALL_WHT` |

Standalone discounts are either **generic** ("ส่วนลด", "คูปองส่วนลด") or **item-specific** ("ส่วนลดไก่ทอด") — referencing an actual item on the receipt.

## Templates

| Template | Description |
| --- | --- |
| `formal_invoice` | A4 tax invoice with full table columns |
| `simple_receipt` | Compact receipt with minimal columns |
| `thermal_pos` | Narrow 320px POS/thermal printer style |

## Project Structure

```text
src/thai_receipt_generator/
├── models.py        # Data classes (LineItem, ReceiptConfig, etc.)
├── calculator.py    # Financial math (discounts, VAT, WHT, totals)
├── combinator.py    # Combinatorial variation engine
├── renderer.py      # HTML → PNG via Playwright
├── cli.py           # Click CLI
└── templates/       # Jinja2 HTML/CSS templates
examples/
├── simple.json              # Basic 2-item receipt with overall VAT
├── bug1_discount_splice.json # Standalone discount + WHT test case
└── full_features.json       # All features: per-item VAT/WHT/discount + standalone + overall
```
