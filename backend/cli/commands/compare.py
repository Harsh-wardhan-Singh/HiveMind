"""HIVEMIND `compare` Command (Phase 9).

Computes and displays differential trajectory analytics between two simulation runs.
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from backend.analytics.comparison import compare_simulation_runs
from backend.events.event_store import EventStore
from backend.persistence.db import create_db_engine_and_factory

console = Console()


def compare_command(
    run_id_a: str = typer.Argument(..., help="Baseline simulation run ID."),
    run_id_b: str = typer.Argument(
        ..., help="Counterfactual branch simulation run ID."
    ),
    metrics: str | None = typer.Option(
        None, "--metrics", "-m", help="Comma-separated list of metrics to compare."
    ),
    database_url: str = typer.Option(
        "sqlite:///hivemind.db",
        "--database-url",
        "--db",
        help="Database connection URL.",
    ),
) -> None:
    """Compare longitudinal trajectories and compute metric divergence across runs."""
    _, factory = create_db_engine_and_factory(database_url)
    store = EventStore(factory)

    metric_list = [m.strip() for m in metrics.split(",")] if metrics else None

    console.print(
        f"[bold cyan]Comparing trajectories:[/] [bold white]{run_id_a}[/] vs [bold white]{run_id_b}[/]..."
    )

    try:
        analysis = compare_simulation_runs(
            event_store=store,
            run_id_a=run_id_a,
            run_id_b=run_id_b,
            metrics=metric_list,
        )
    except (ValueError, KeyError, RuntimeError) as e:
        console.print(f"[bold red]Error computing comparison:[/] {e}")
        raise typer.Exit(code=1) from e

    if analysis.ticks_compared == 0:
        console.print(
            "[yellow]Warning:[/] No overlapping days found between the two runs to compare."
        )
        return

    # Rich formatted Comparative Table
    table = Table(
        title=f"Differential Trajectory Comparison: {analysis.name_a} vs {analysis.name_b}",
        expand=True,
    )
    table.add_column("Societal / Macro Metric", style="bold cyan")
    table.add_column(
        f"Baseline: {analysis.name_a[:18]}", justify="right", style="white"
    )
    table.add_column(f"Branch: {analysis.name_b[:18]}", justify="right", style="white")
    table.add_column("Terminal Delta (Δ)", justify="right")
    table.add_column("Δ %", justify="right")

    for m_name, s in analysis.summaries.items():
        diff = s.final_diff
        pct = s.final_pct_diff

        # Color coding: For unrest, positive diff is bad (red); for GDP/Approval, positive is good (green)
        if m_name in ("city_unrest", "cpi", "unemployment_rate"):
            delta_color = (
                "red" if diff > 0.001 else ("green" if diff < -0.001 else "dim")
            )
        else:
            delta_color = (
                "green" if diff > 0.001 else ("red" if diff < -0.001 else "dim")
            )

        table.add_row(
            m_name,
            f"{s.final_val_a:,.2f}",
            f"{s.final_val_b:,.2f}",
            f"[{delta_color}]{diff:+,.2f}[/]",
            f"[{delta_color}]{pct:+.1f}%[/]",
        )

    meta_text = (
        f"[dim]Window: Day {analysis.start_tick} -> Day {analysis.end_tick} "
        f"({analysis.ticks_compared} days compared) | Fork Tick: {analysis.fork_tick}[/]\n"
        f"[bold]Qualitative Impact Verdict:[/] [italic bright_yellow]{analysis.qualitative_verdict}[/]"
    )

    console.print("\n", table)
    console.print(Panel(meta_text, border_style="dim", padding=(0, 1)))
