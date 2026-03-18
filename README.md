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

# Clean up generated files
./scripts/clean.sh
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
    { "name": "ส่วนลดไก่ทอด", "amount": 20, "position": 1 }
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
| `has_wht` | no | false | Per-item WHT (services only) |
| `wht_rate` | no | 3 | WHT percentage (1, 2, 3, or 5) |
| `discount` | no | none | `{"type": "absolute"/"percentage", "value": N}` |

**Standalone discount fields:**

| Field | Required | Default | Description |
| --- | --- | --- | --- |
| `name` | no | ส่วนลด | Generic or item-specific (e.g. "ส่วนลดไก่ทอด") |
| `amount` | yes | - | Absolute discount amount |
| `position` | no | -1 (end) | Where to insert among items (1 = after first item) |

**Receipt-level fields:**

| Field | Default | Description |
| --- | --- | --- |
| `template` | formal_invoice | Template name |
| `overall_discount` | none | Discount on entire receipt |
| `overall_vat` | false | VAT 7% on entire receipt |
| `overall_wht` | false | WHT on entire receipt |

See `examples/` for ready-to-use JSON files.

## Configuration (.env)

All batch settings live in `.env`. CLI flags override `.env` values.

```bash
# ── General ──────────────────────────────────────
RECEIPT_JSON_DIR=generated_json    # where gen-json writes JSON configs
RECEIPT_OUTPUT_DIR=output          # where render writes PNG images
RECEIPT_DPI=150                    # image resolution (150 = good for OCR)

# ── Batch generation (thai-receipt-gen gen-json) ─
RECEIPT_ITEMS=1,2,3                # receipt variations with 1, 2, and 3 items
RECEIPT_TMPL_FORMAL_INVOICE=true   # A4 tax invoice with full table
RECEIPT_TMPL_SIMPLE_RECEIPT=true   # compact shop receipt
RECEIPT_TMPL_THERMAL_POS=true      # narrow POS/thermal printer style
RECEIPT_MAX_COMBOS=50              # sample 50 from all combinations (remove for all)
RECEIPT_SEED=42                    # same seed = same samples every time

# ── Variation axes (true = always on, false = always off, vary = both) ─
RECEIPT_PER_ITEM_VAT=vary          # per-item VAT 7%
RECEIPT_PER_ITEM_WHT=vary          # per-item WHT (services only)
RECEIPT_PER_ITEM_DISCOUNT=vary     # per-item discount (absolute/percentage)
RECEIPT_STANDALONE_DISCOUNT=vary   # standalone discount rows
RECEIPT_OVERALL_DISCOUNT=vary      # overall receipt discount
RECEIPT_OVERALL_VAT=vary           # overall VAT on entire receipt
RECEIPT_OVERALL_WHT=vary           # overall WHT on entire receipt
```

## CLI Reference

| Command | Description |
| --- | --- |
| `thai-receipt-gen gen-json` | Step 1: generate JSON configs into `generated_json/` |
| `thai-receipt-gen render <dir>` | Step 2: render all JSONs in a directory to PNGs |
| `thai-receipt-gen single <file>` | Render one JSON to one PNG |
| `thai-receipt-gen list-combos` | Dry run: count combinations without generating |
| `./scripts/clean.sh` | Delete `generated_json/` and `output/` |

## Variation Axes

Each axis accepts `true`, `false`, or `vary`:

| Axis | Env var | Description |
| --- | --- | --- |
| Per-item VAT | `RECEIPT_PER_ITEM_VAT` | VAT 7% on individual items |
| Per-item WHT | `RECEIPT_PER_ITEM_WHT` | Withholding tax (services only, never products) |
| Per-item discount | `RECEIPT_PER_ITEM_DISCOUNT` | Discount on individual items (absolute or %) |
| Standalone discount | `RECEIPT_STANDALONE_DISCOUNT` | Separate discount rows (generic or item-specific) |
| Overall discount | `RECEIPT_OVERALL_DISCOUNT` | Discount on entire receipt |
| Overall VAT | `RECEIPT_OVERALL_VAT` | VAT 7% on entire receipt |
| Overall WHT | `RECEIPT_OVERALL_WHT` | WHT on entire receipt |

**Rules:**

- WHT is only applied to **service** items (ค่าที่ปรึกษา, บริการซ่อมแอร์), never products (ไก่ทอด, กาแฟ)
- Overall VAT/WHT and per-item VAT/WHT are mutually exclusive (combinator filters automatically)
- Standalone discounts can be **generic** ("ส่วนลด") or **item-specific** ("ส่วนลดไก่ทอด") and appear at varying positions among items

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
├── simple.json                  # Basic 2-item receipt with overall VAT
├── bug1_discount_splice.json    # Standalone discount + WHT test case
├── discount_between_items.json  # Positioned discounts between items
└── full_features.json           # All features combined
scripts/
└── clean.sh                     # Delete generated_json/ and output/
```
