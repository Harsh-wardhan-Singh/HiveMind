"""HIVEMIND `branch` Command (Phase 9).

Forks an existing historical simulation run into a counterfactual branch with policy overrides.
"""

import time
import uuid
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from backend.app.config import CityConfig, SimulationConfig
from backend.events.event_store import EventStore
from backend.persistence.db import create_db_engine_and_factory
from backend.simulation.engine import SimulationEngine

console = Console()


def branch_command(
    run_id: str = typer.Argument(..., help="Parent simulation run ID to fork from."),
    fork_tick: int = typer.Option(
        ..., "--tick", "-t", help="Historical day (tick) to fork at."
    ),
    branch_name: str = typer.Option(
        "Counterfactual Branch",
        "--name",
        "-n",
        help="Name for the new branch timeline.",
    ),
    branch_run_id: str | None = typer.Option(
        None,
        "--branch-id",
        "-b",
        help="Custom branch run ID (auto-generated if omitted).",
    ),
    subsidy: float | None = typer.Option(
        None, "--subsidy", help="Food subsidy rate override [0.0 - 0.50]."
    ),
    austerity: float | None = typer.Option(
        None, "--austerity", help="Austerity magnitude [0.0 - 1.0]."
    ),
    stimulus: float | None = typer.Option(
        None, "--stimulus", help="Welfare stimulus grant amount per capita."
    ),
    public_works: float | None = typer.Option(
        None, "--public-works", help="Civic public works daily wage."
    ),
    corporate_tax: float | None = typer.Option(
        None, "--corp-tax", help="Corporate profit tax rate override [0.0 - 1.0]."
    ),
    income_tax_high: float | None = typer.Option(
        None, "--income-tax", help="High-income bracket tax rate override [0.0 - 1.0]."
    ),
    treasury_grant: float | None = typer.Option(
        None, "--grant", help="Municipal treasury injection cash amount."
    ),
    days_to_advance: int = typer.Option(
        0,
        "--days",
        "-d",
        help="Days to advance the branch forward immediately after forking.",
    ),
    database_url: str = typer.Option(
        "sqlite:///hivemind.db",
        "--database-url",
        "--db",
        help="Database connection URL.",
    ),
) -> None:
    """Fork an active or historical simulation into a counterfactual timeline."""
    _, factory = create_db_engine_and_factory(database_url)
    store = EventStore(factory)
    parent_meta = store.get_run(run_id)

    if not parent_meta:
        console.print(
            f"[bold red]Error:[/] Parent run '{run_id}' not found in database."
        )
        raise typer.Exit(code=1)

    b_run_id = branch_run_id or f"{run_id}_fork_{uuid.uuid4().hex[:6]}"

    # Assemble policy overrides
    overrides: dict[str, Any] = {}
    if subsidy is not None:
        overrides["FOOD_SUBSIDY"] = subsidy
    if austerity is not None:
        overrides["AUSTERITY"] = austerity
    if stimulus is not None:
        overrides["WELFARE_STIMULUS"] = stimulus
    if public_works is not None:
        overrides["PUBLIC_WORKS"] = public_works
    if treasury_grant is not None:
        overrides["treasury_grant"] = treasury_grant

    tax_overrides: dict[str, float] = {}
    if corporate_tax is not None:
        tax_overrides["corporate_tax"] = corporate_tax
    if income_tax_high is not None:
        tax_overrides["income_tax_high"] = income_tax_high
    if tax_overrides:
        overrides["tax_rates"] = tax_overrides

    console.print(
        f"[bold cyan]Forking timeline from parent '{run_id}' at Day {fork_tick}...[/]"
    )

    # Create parent engine container to orchestrate fork
    parent_config = SimulationConfig(
        run_id=run_id,
        seed=parent_meta["seed"],
        total_days=parent_meta["total_days"],
        database_url=database_url,
        city=CityConfig(starting_population=20),
    )

    with SimulationEngine(parent_config, event_store=store) as parent_engine:
        # Fork branch engine
        branch_engine = parent_engine.fork(
            branch_name=branch_name,
            fork_tick=fork_tick,
            branch_run_id=b_run_id,
            policy_overrides=overrides,
        )

        console.print(
            f"[bold green]✔ Branch created:[/] [bold white]{b_run_id}[/] ('{branch_name}')"
        )

        # Advance if requested
        if days_to_advance > 0:
            console.print(
                f"[bold cyan]Stepping branch timeline forward by {days_to_advance} days...[/]"
            )
            t_start = time.time()
            for _ in range(days_to_advance):
                branch_engine.step()
            dur = time.time() - t_start
            console.print(
                f"[bold green]✔ Branch advanced to Day {branch_engine.state.clock.current_tick}[/] "
                f"({days_to_advance} ticks in {dur:.2f}s)"
            )
            branch_engine.save_snapshot()

        # Display branch lineage card
        table = Table(box=None, expand=True)
        table.add_column("Attribute", style="bold cyan")
        table.add_column("Value", style="bold white")

        table.add_row("Branch Run ID", b_run_id)
        table.add_row("Branch Name", branch_name)
        table.add_row("Parent Run ID", run_id)
        table.add_row("Fork Point", f"Day {fork_tick}")
        table.add_row("Current Day", f"Day {branch_engine.state.clock.current_tick}")
        table.add_row("Policy Interventions", str(overrides) if overrides else "None")

        m = branch_engine.state.metrics
        table.add_section()
        table.add_row("Treasury Balance", f"{m.treasury_balance:,.2f} C")
        table.add_row("Citizen Approval", f"{m.approval_rating:.1f}%")
        table.add_row("Civil Unrest Score", f"{m.city_unrest:.2f}")

        panel = Panel(
            table,
            title="[bold purple]🔀 Counterfactual Branch Summary[/]",
            border_style="purple",
            padding=(1, 2),
        )
        console.print(panel)
        console.print(
            f"[dim]To compare this branch against baseline:\n"
            f" [bold white]hivemind compare {run_id} {b_run_id}[/][/]\n"
        )
        branch_engine.close()
