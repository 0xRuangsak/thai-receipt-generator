from __future__ import annotations

import asyncio
import base64
from pathlib import Path

from jinja2 import Environment, PackageLoader
from playwright.async_api import async_playwright

from .models import CalculatedLineItem, ReceiptCalculation, StandaloneDiscount

FONT_PATH = Path(__file__).resolve().parent.parent.parent / "fonts" / "NotoSansThai.ttf"


def _load_font_base64() -> str:
    return base64.b64encode(FONT_PATH.read_bytes()).decode("ascii")


def _format_thai_currency(value: object) -> str:
    return f"{float(value):,.2f}"


def _build_jinja_env() -> Environment:
    env = Environment(
        loader=PackageLoader("thai_receipt_generator", "templates"),
        autoescape=False,
    )
    env.filters["float"] = float
    env.tests["line_item"] = lambda x: isinstance(x, CalculatedLineItem)
    env.tests["standalone_discount"] = lambda x: isinstance(x, StandaloneDiscount)
    return env


def _render_html(
    env: Environment,
    receipt: ReceiptCalculation,
    font_b64: str,
    invoice_no: str,
    date: str,
    due_date: str,
) -> str:
    template = env.get_template(f"{receipt.config.template_name}.html")
    return template.render(
        receipt=receipt,
        font_base64=font_b64,
        invoice_no=invoice_no,
        date=date,
        due_date=due_date,
    )


async def _render_batch_async(
    receipts: list[ReceiptCalculation],
    output_dir: Path,
    dpi: int = 150,
) -> list[Path]:
    font_b64 = _load_font_base64()
    env = _build_jinja_env()
    output_dir.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(device_scale_factor=dpi / 96)

        for i, receipt in enumerate(receipts):
            vid = receipt.config.variation_id or f"receipt_{i:04d}"
            invoice_no = f"2026-{i:04d}"
            date = "18/03/2026"
            due_date = "31/03/2026"

            html = _render_html(env, receipt, font_b64, invoice_no, date, due_date)
            await page.set_content(html, wait_until="networkidle")

            out_path = output_dir / f"{vid}.png"
            body = page.locator("body")
            await body.screenshot(path=str(out_path))
            paths.append(out_path)

        await browser.close()

    return paths


def render_batch(
    receipts: list[ReceiptCalculation],
    output_dir: Path,
    dpi: int = 150,
) -> list[Path]:
    """Synchronous wrapper around the async renderer."""
    return asyncio.run(_render_batch_async(receipts, output_dir, dpi))
