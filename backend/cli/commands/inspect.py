"""HIVEMIND `inspect` Command Suite (Phase 9).

Provides diagnostics for runs, citizens, corporations, districts, events, and metrics.
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from backend.events.event_store import EventStore
from backend.persistence.db import create_db_engine_and_factory
from backend.persistence.snapshot import deserialize_world_state

console = Console()
inspect_app = typer.Typer(
    help="Inspect simulation entities, agents, firms, and metrics."
)


def _get_event_store(database_url: str) -> EventStore:
    _, factory = create_db_engine_and_factory(database_url)
    return EventStore(factory)


@inspect_app.command("run")
def inspect_run(
    run_id: str = typer.Argument(..., help="Simulation run identifier to inspect."),
    database_url: str = typer.Option(
        "sqlite:///hivemind.db",
        "--database-url",
        "--db",
        help="Database connection URL.",
    ),
) -> None:
    """Display comprehensive overview of a simulation run and its lineage."""
    store = _get_event_store(database_url)
    run_meta = store.get_run(run_id)

    if not run_meta:
        console.print(f"[bold red]Error:[/] Run '{run_id}' not found in database.")
        raise typer.Exit(code=1)

    child_runs = store.get_child_runs(run_id)
    snapshots = store.get_all_snapshots(run_id)
    events = store.get_events(run_id)

    table = Table(box=None, expand=True)
    table.add_column("Metadata", style="bold cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Run Identifier", run_meta["run_id"])
    table.add_row("City Name", run_meta.get("name") or "Hivemind City")
    table.add_row("PRNG Seed", str(run_meta["seed"]))
    table.add_row("Target Duration", f"{run_meta['total_days']} days")
    table.add_row(
        "Parent Run ID", run_meta.get("parent_run_id") or "None (Root Baseline)"
    )
    if run_meta.get("fork_tick") is not None:
        table.add_row("Fork Tick", str(run_meta["fork_tick"]))
    table.add_row("Total Recorded Events", f"{len(events):,}")
    table.add_row("Saved Snapshots Count", f"{len(snapshots)}")
    table.add_row("Child Branches Forked", f"{len(child_runs)}")

    # Show latest snapshot metrics if available
    latest_snap = store.get_latest_snapshot(run_id)
    if latest_snap and "state_blob" in latest_snap:
        blob = latest_snap["state_blob"]
        m = blob.get("metrics", {})
        table.add_section()
        table.add_row("Latest Snapshot Tick", f"Day {latest_snap['tick']}")
        table.add_row("Terminal Population", str(m.get("alive_population", "N/A")))
        table.add_row("Terminal GDP", f"{m.get('gdp', 0):,.2f} C")
        table.add_row("Terminal CPI", f"{m.get('cpi', 0):.2f}")
        table.add_row("Approval Rating", f"{m.get('approval_rating', 0):.1f}%")
        table.add_row("Civil Unrest", f"{m.get('city_unrest', 0):.2f}")
        table.add_row(
            "Society Harmony", f"{m.get('society_harmony_index', 0) * 100:.1f}%"
        )

    panel = Panel(
        table,
        title=f"[bold green]🔍 Simulation Run Diagnostics: {run_id}[/]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(panel)

    if child_runs:
        console.print("\n[bold cyan]🌿 Counterfactual Child Branches:[/]")
        b_table = Table(box=None, expand=True)
        b_table.add_column("Branch Run ID", style="bold white")
        b_table.add_column("Branch Name", style="cyan")
        b_table.add_column("Fork Day", justify="right", style="yellow")
        for cr in child_runs:
            b_table.add_row(
                cr["run_id"], cr.get("name") or "Unnamed", f"Day {cr['fork_tick']}"
            )
        console.print(b_table)


@inspect_app.command("agent")
def inspect_agent(
    agent_id: str = typer.Argument(..., help="Agent ID (e.g. agent_0001)."),
    run_id: str | None = typer.Option(
        None, "--run-id", "-r", help="Run ID (defaults to latest recorded run)."
    ),
    database_url: str = typer.Option(
        "sqlite:///hivemind.db",
        "--database-url",
        "--db",
        help="Database connection URL.",
    ),
) -> None:
    """Inspect detailed citizen profile, OCEAN personality, financials, and beliefs."""
    store = _get_event_store(database_url)
    snap = store.get_latest_snapshot(run_id) if run_id else None
    if not snap:
        # Try finding snapshot with the agent
        all_snaps = store.get_all_snapshots(run_id or "")
        snap = all_snaps[-1] if all_snaps else None

    if not snap or "state_blob" not in snap:
        console.print(
            f"[bold red]Error:[/] No state snapshot found to inspect agent '{agent_id}'."
        )
        raise typer.Exit(code=1)

    state = deserialize_world_state(snap["state_blob"])
    agent = state.agents.get(agent_id)

    if not agent:
        console.print(f"[bold red]Error:[/] Agent '{agent_id}' not found in state.")
        raise typer.Exit(code=1)

    table = Table(box=None, expand=True)
    table.add_column("Attribute", style="bold cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Agent ID", agent.id)
    table.add_row("Biological Age", f"{agent.age_years} years ({agent.age_days} days)")
    table.add_row("Sex & Role", f"{agent.sex} | [bold yellow]{agent.role.value}[/]")
    table.add_row(
        "Life Status",
        "[bold green]ALIVE[/]" if agent.alive else "[bold red]DECEASED[/]",
    )
    table.add_row("Health Score", f"{agent.health * 100:.1f}%")
    table.add_row("Cash Reserves", f"{agent.cash:,.2f} C")
    table.add_row("Bank Deposit", f"{agent.bank_deposit:,.2f} C")
    table.add_row("Assigned District", agent.district_id or "Unassigned")
    table.add_row("Household", agent.household_id or "Independent")
    table.add_row("Employer Company", agent.employer_id or "Unemployed")
    table.add_row("Citizen Favorability", f"{agent.favorability:.2f}")
    table.add_row("Civil Unrest", f"{agent.unrest:.2f}")

    table.add_section()
    # Big Five Personality Radar
    p = agent.personality
    table.add_row("Openness to Exp.", f"{p.openness:.2f}")
    table.add_row("Conscientiousness", f"{p.conscientiousness:.2f}")
    table.add_row("Extraversion", f"{p.extraversion:.2f}")
    table.add_row("Agreeableness", f"{p.agreeableness:.2f}")
    table.add_row("Neuroticism", f"{p.neuroticism:.2f}")
    table.add_row("Risk Tolerance", f"{p.risk_tolerance:.2f}")
    table.add_row("Social Trust", f"{p.social_trust:.2f}")
    table.add_row("Ambition", f"{p.ambition:.2f}")

    # Rumor beliefs
    beliefs = state.rumor_engine.agent_beliefs.get(agent.id, {})
    if beliefs:
        table.add_section()
        for topic, b_score in beliefs.items():
            table.add_row(f"Rumor Belief: '{topic}'", f"{b_score:.2f}")

    panel = Panel(
        table,
        title=f"[bold green]👤 Citizen Profile: {agent.id}[/]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(panel)


@inspect_app.command("company")
def inspect_company(
    company_id: str = typer.Argument(..., help="Company ID (e.g. comp_food_01)."),
    run_id: str | None = typer.Option(None, "--run-id", "-r", help="Run ID."),
    database_url: str = typer.Option(
        "sqlite:///hivemind.db",
        "--database-url",
        "--db",
        help="Database connection URL.",
    ),
) -> None:
    """Inspect corporate firm financials, inventory, payroll, and stock."""
    store = _get_event_store(database_url)
    snap = store.get_latest_snapshot(run_id) if run_id else None
    if not snap or "state_blob" not in snap:
        console.print(
            f"[bold red]Error:[/] No snapshot found to inspect company '{company_id}'."
        )
        raise typer.Exit(code=1)

    state = deserialize_world_state(snap["state_blob"])
    comp = state.companies.get(company_id)

    if not comp:
        console.print(f"[bold red]Error:[/] Company '{company_id}' not found in state.")
        raise typer.Exit(code=1)

    table = Table(box=None, expand=True)
    table.add_column("Corporate Metric", style="bold cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Company ID", comp.id)
    table.add_row("Company Name", comp.name)
    table.add_row("Stock Ticker", f"[bold yellow]{comp.ticker}[/]")
    table.add_row("Operating District", comp.district_id)
    comm_str = (
        comp.commodity_type.value
        if hasattr(comp.commodity_type, "value")
        else str(comp.commodity_type)
    )
    table.add_row("Produced Commodity", comm_str)
    table.add_row(
        "Solvency Status",
        "[bold green]SOLVENT[/]" if comp.solvency else "[bold red]INSOLVENT[/]",
    )
    table.add_row("Cash Reserves", f"{comp.cash:,.2f} C")
    table.add_row("Physical Capital (K)", f"{comp.capital:,.1f}")
    table.add_row("Inventory In Stock", f"{comp.inventory:,.1f} units")
    table.add_row("Target Wage", f"{comp.target_wage:.2f} C/day")
    table.add_row("Employee Count", f"{len(comp.employee_ids)} workers")
    table.add_row("Shares Outstanding", f"{comp.shares_outstanding:,}")
    table.add_row("Daily Net Profit", f"{comp.daily_profit:,.2f} C")

    panel = Panel(
        table,
        title=f"[bold cyan]🏢 Corporate Enterprise: {comp.name}[/]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)


@inspect_app.command("district")
def inspect_district(
    district_id: str = typer.Argument(..., help="District ID (e.g. dist_central)."),
    run_id: str | None = typer.Option(None, "--run-id", "-r", help="Run ID."),
    database_url: str = typer.Option(
        "sqlite:///hivemind.db",
        "--database-url",
        "--db",
        help="Database connection URL.",
    ),
) -> None:
    """Inspect district civil stability, safety, rent, and riot status."""
    store = _get_event_store(database_url)
    snap = store.get_latest_snapshot(run_id) if run_id else None
    if not snap or "state_blob" not in snap:
        console.print(
            f"[bold red]Error:[/] No snapshot found to inspect district '{district_id}'."
        )
        raise typer.Exit(code=1)

    state = deserialize_world_state(snap["state_blob"])
    dist = state.districts.get(district_id)

    if not dist:
        console.print(
            f"[bold red]Error:[/] District '{district_id}' not found in state."
        )
        raise typer.Exit(code=1)

    # Count resident citizens
    residents = sum(
        1 for a in state.agents.values() if a.district_id == dist.id and a.alive
    )

    table = Table(box=None, expand=True)
    table.add_column("District Metric", style="bold cyan")
    table.add_column("Value", style="bold white")

    table.add_row("District ID", dist.id)
    table.add_row("District Name", dist.name)
    table.add_row("Resident Citizens", f"{residents} residents")
    table.add_row("Safety Score", f"{dist.safety_score * 100:.1f}%")
    table.add_row("Base Monthly Rent", f"{dist.rent:,.1f} C")
    table.add_row("Land Price", f"{dist.land_price:,.1f} C")
    table.add_row("Housing Capacity", f"{dist.housing_units} units")
    table.add_row("Civil Unrest Score", f"{dist.unrest_score:.2f}")

    r_status = (
        f"[bold red]RIOTS ACTIVE ({dist.riot_days} days)[/]"
        if dist.is_rioting
        else "[bold green]PEACEFUL[/]"
    )
    table.add_row("Public Order Status", r_status)

    panel = Panel(
        table,
        title=f"[bold yellow]📍 Municipal District: {dist.name}[/]",
        border_style="yellow",
        padding=(1, 2),
    )
    console.print(panel)


@inspect_app.command("events")
def inspect_events(
    run_id: str = typer.Argument(..., help="Run ID to inspect events from."),
    event_type: str | None = typer.Option(
        None, "--type", "-t", help="Filter by event type."
    ),
    limit: int = typer.Option(25, "--limit", "-n", help="Max events to display."),
    database_url: str = typer.Option(
        "sqlite:///hivemind.db",
        "--database-url",
        "--db",
        help="Database connection URL.",
    ),
) -> None:
    """Stream chronological event log with optional type filter."""
    store = _get_event_store(database_url)
    events = store.get_events(run_id)

    if event_type:
        events = [e for e in events if e.event_type.lower() == event_type.lower()]

    if not events:
        console.print(f"[dim]No matching events found for run '{run_id}'.[/]")
        return

    table = Table(box=None, expand=True)
    table.add_column("Tick", justify="right", width=6, style="yellow")
    table.add_column("Event Type", width=25, style="bold cyan")
    table.add_column("Key Details", ratio=1, style="white")

    for e in events[-limit:]:
        details = str(e.payload)[:80]
        table.add_row(f"Day {e.tick}", e.event_type, details)

    panel = Panel(
        table,
        title=f"[bold green]📜 Event Stream ({len(events)} total events)[/]",
        border_style="green",
        padding=(0, 1),
    )
    console.print(panel)
