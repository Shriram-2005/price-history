"""Typer CLI interface for Price History.

Provides rich visual tables, timeline comparisons, and DPDP-compliant data control.
"""

from __future__ import annotations

import sys
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.adapters.swiggy.adapter import SwiggyInstamartAdapter
from src.adapters.swiggy.auth import (
    run_oauth_flow,
    get_token_file_path,
    load_saved_token,
    revoke_session,
)
from src.core.storage import Storage, get_default_db_path
from src.core.sync import SyncOrchestrator

app = typer.Typer(
    name="price-history",
    help="Personal price-intelligence for quick-commerce grocery orders (Swiggy Instamart).",
    add_completion=False,
)
console = Console(highlight=False)


@app.command()
def login():
    """Connects your live Swiggy account via official OAuth 2.1 PKCE in your browser."""
    console.print(Panel.fit(
        "[bold cyan]Swiggy Builders Club — Connect Live Account[/bold cyan]\n"
        "[dim]Opening your browser to log in with your Swiggy phone number + OTP...[/dim]",
        box=box.ROUNDED,
    ))

    try:
        tokens = run_oauth_flow()
        console.print(Panel.fit(
            f"[bold green]✓ Successfully Authenticated![/bold green]\n"
            f"[white]Access token saved securely to:[/white] [dim]{get_token_file_path()}[/dim]\n"
            f"[yellow]Valid for:[/yellow] {tokens.get('expires_in', 432000) // 86400} days\n\n"
            f"[bold white]Next step:[/bold white] Run [bold cyan]python -m src.cli.main sync[/bold cyan] to pull your real orders!",
            box=box.ROUNDED,
        ))
    except Exception as e:
        console.print(f"[bold red]Login failed:[/bold red] {e}")


@app.command()
def sync(
    demo: bool = typer.Option(
        False,
        "--demo",
        "-d",
        help="Use synthetic demo orders (allows testing offline without OAuth token).",
    ),
    token: str = typer.Option(
        None,
        "--token",
        "-t",
        help="Swiggy OAuth Bearer token (or set SWIGGY_ACCESS_TOKEN env var).",
    ),
):
    """Syncs recent Instamart orders into the local SQLite Price Vault."""
    storage = Storage()
    adapter = SwiggyInstamartAdapter(access_token=token, use_demo_data=demo)
    orchestrator = SyncOrchestrator(storage, adapter)

    source_label = "Demo Order Fixtures" if adapter.use_demo_data else "Live Swiggy Instamart MCP"
    console.print(Panel.fit(f"[bold cyan]Syncing from {source_label}...[/bold cyan]", box=box.ROUNDED))

    with console.status("[bold green]Pulling orders and normalizing pack sizes...[/bold green]"):
        result = orchestrator.run_sync()

    table = Table(title="Sync Run Completed", box=box.ROUNDED)
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="bold green")

    table.add_row("Orders Inspected", str(result["orders_seen"]))
    table.add_row("New Orders Stored", str(result["orders_new"]))
    table.add_row("Price Observations Created", str(result["observations_created"]))
    table.add_row("Duration", f"{result['duration_seconds']}s")
    table.add_row("Database Location", str(storage.db_path))

    console.print(table)


@app.command()
def list():
    """Lists all canonical products currently tracked in your local database."""
    storage = Storage()
    products = storage.get_all_products()

    if not products:
        console.print("[yellow]No products tracked yet. Run 'price-history sync --demo' first to import orders.[/yellow]")
        return

    table = Table(title="Tracked Grocery Staples", box=box.ROUNDED)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Brand", style="magenta")
    table.add_column("Canonical Product Name", style="bold white")
    table.add_column("Pack Size", style="cyan")
    table.add_column("Base Unit", style="green")

    for p in products:
        pack_label = f"{p.pack_size_base} {p.base_unit.value}"
        if p.base_unit.value == "ml" and p.pack_size_base >= 1000:
            pack_label = f"{p.pack_size_base / 1000:g} L"
        elif p.base_unit.value == "g" and p.pack_size_base >= 1000:
            pack_label = f"{p.pack_size_base / 1000:g} kg"

        table.add_row(
            str(p.id),
            p.brand or "-",
            p.canonical_name,
            pack_label,
            p.base_unit.value,
        )

    console.print(table)


@app.command()
def timeline(
    query: str = typer.Argument(..., help="Search query for the product (e.g. 'oil', 'milk', 'atta')")
):
    """Shows the chronological price history and percentage changes for a product."""
    storage = Storage()
    products = storage.get_all_products()

    # Search for matching product
    matches = [
        p for p in products 
        if query.lower() in p.canonical_name.lower() or (p.brand and query.lower() in p.brand.lower())
    ]

    if not matches:
        console.print(f"[red]No tracked product matching '{query}' found.[/red]")
        console.print("[dim]Tip: Run 'price-history list' to see all tracked products.[/dim]")
        return

    for product in matches:
        timeline_points = storage.get_timeline_for_product(product.id)
        if not timeline_points:
            continue

        pack_label = f"{product.pack_size_base} {product.base_unit.value}"
        if product.base_unit.value == "ml" and product.pack_size_base >= 1000:
            pack_label = f"{product.pack_size_base / 1000:g} L"
        elif product.base_unit.value == "g" and product.pack_size_base >= 1000:
            pack_label = f"{product.pack_size_base / 1000:g} kg"

        console.print(f"\n[bold underline]{product.canonical_name} ({pack_label})[/bold underline]")

        table = Table(box=box.ROUNDED)
        table.add_column("Order Date", style="cyan")
        table.add_column("Order ID", style="dim")
        table.add_column("Qty", justify="right")
        table.add_column("Total Paid", justify="right", style="white")
        table.add_column("Unit Price", justify="right", style="bold yellow")
        table.add_column("Change vs Last", justify="center")

        for pt in timeline_points:
            date_str = pt.date.strftime("%d %b %Y")
            total_str = f"₹{pt.total_paid_inr:.2f}"
            unit_price_str = f"₹{pt.unit_price_inr:.2f} / {pt.standard_unit_label.split('/')[-1].strip()}"

            if pt.change_vs_previous_pct is None:
                change_str = "[dim]Baseline[/dim]"
            elif pt.flag_higher:
                change_str = f"[bold red]+{pt.change_vs_previous_pct:.1f}% ⚠️ HIGHER[/bold red]"
            elif pt.change_vs_previous_pct > 0:
                change_str = f"[yellow]+{pt.change_vs_previous_pct:.1f}%[/yellow]"
            elif pt.change_vs_previous_pct < 0:
                change_str = f"[bold green]{pt.change_vs_previous_pct:.1f}% CHEAPER[/bold green]"
            else:
                change_str = "[dim]0.0% (Same)[/dim]"

            table.add_row(
                date_str,
                pt.order_id,
                str(pt.quantity),
                total_str,
                unit_price_str,
                change_str,
            )

        console.print(table)


@app.command()
def check(
    query: str = typer.Argument(..., help="Product title to compare (e.g. 'Fortune Sunlite 1L')"),
    demo: bool = typer.Option(True, "--demo", "-d", help="Use demo live store search"),
):
    """Compares today's live store price against your last recorded purchase price."""
    storage = Storage()
    adapter = SwiggyInstamartAdapter(use_demo_data=demo)

    console.print(f"[bold cyan]Checking live Instamart store for '{query}'...[/bold cyan]")
    live_results = adapter.search_products(query)

    if not live_results:
        console.print(f"[yellow]No live products found matching '{query}'.[/yellow]")
        return

    table = Table(title="Live Store Price vs. Your Last Paid Price", box=box.ROUNDED)
    table.add_column("Product Listing", style="white")
    table.add_column("Live Store Price", style="bold yellow", justify="right")
    table.add_column("Your Last Paid", style="cyan", justify="right")
    table.add_column("Comparison", justify="center")

    products = storage.get_all_products()

    for item in live_results:
        live_price = float(item["price"])
        item_name = item["name"]

        # Find matching product in local DB
        matched_points = []
        for p in products:
            if p.canonical_name.lower() in item_name.lower():
                pts = storage.get_timeline_for_product(p.id)
                if pts:
                    matched_points.extend(pts)

        if matched_points:
            last_pt = matched_points[-1]
            last_paid = last_pt.total_paid_inr
            diff_pct = round(((live_price - last_paid) / last_paid) * 100, 1)

            if diff_pct > 0:
                comp_str = f"[bold red]+{diff_pct:.1f}% (Pricier today)[/bold red]"
            elif diff_pct < 0:
                comp_str = f"[bold green]{diff_pct:.1f}% (Deal! Cheaper today)[/bold green]"
            else:
                comp_str = "[dim]Same price[/dim]"

            last_paid_str = f"₹{last_paid:.2f} ({last_pt.date.strftime('%d %b')})"
        else:
            last_paid_str = "[dim]No past purchase[/dim]"
            comp_str = "[dim]-[/dim]"

        table.add_row(
            item_name,
            f"₹{live_price:.2f}",
            last_paid_str,
            comp_str,
        )

    console.print(table)


@app.command()
def purge(
    confirm: bool = typer.Option(
        False,
        "--confirm",
        help="Acknowledge that all local price history data and tokens will be permanently deleted.",
    )
):
    """DPDP Erasure: Permanently removes all local database tables, orders, and observations."""
    if not confirm:
        console.print("[bold red]Action Required:[/bold red] To permanently purge your local database, pass [yellow]--confirm[/yellow]")
        return

    storage = Storage()
    storage.purge_all_data()
    revoke_session()
    console.print(Panel.fit("[bold green]Success: All local order history, line items, price observations, and OAuth sessions were permanently purged and revoked.[/bold green]", box=box.ROUNDED))


if __name__ == "__main__":
    app()
