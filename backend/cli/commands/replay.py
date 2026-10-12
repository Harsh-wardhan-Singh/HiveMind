"""HIVEMIND `replay` Command (Phase 9).

Reconstructs historical simulation states from immutable event logs and verifies determinism parity.
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from backend.events.event_store import EventStore
from backend.persistence.db import create_db_engine_and_factory
from backend.persistence.snapshot import deserialize_world_state
from backend.replay.replayer import EventReplayer, verify_replay_determinism

console = Console()


def replay_command(
    run_id: str = typer.Argument(..., help="Run ID whose timeline to replay."),
    target_tick: int | None = typer.Option(
        None,
        "--tick",
        "-t",
        help="Historical day (tick) to reconstruct state at (defaults to latest).",
    ),
    verify: bool = typer.Option(
        True,
        "--verify/--no-verify",
        help="Verify bit-for-bit parity against recorded snapshot.",
    ),
    database_url: str = typer.Option(
        "sqlite:///hivemind.db",
        "--database-url",
        "--db",
        help="Database connection URL.",
    ),
) -> None:
    """Replay event streams and reconstruct authoritative historical states."""
    _, factory = create_db_engine_and_factory(database_url)
    store = EventStore(factory)
    run_meta = store.get_run(run_id)

    if not run_meta:
        console.print(f"[bold red]Error:[/] Run '{run_id}' not found in database.")
        raise typer.Exit(code=1)

    all_events = store.get_events(run_id)
    if not all_events:
        console.print(f"[bold red]Error:[/] No events found for run '{run_id}'.")
        raise typer.Exit(code=1)

    max_tick = max(e.tick for e in all_events)
    tick_to_reconstruct = target_tick if target_tick is not None else max_tick

    console.print(
        f"[bold cyan]Reconstructing historical WorldState for run '{run_id}' at Day {tick_to_reconstruct}...[/]"
    )

    replayer = EventReplayer(store)
    reconstructed_state = replayer.reconstruct_state_at_tick(
        run_id, tick_to_reconstruct
    )

    if not reconstructed_state:
        console.print(
            f"[bold red]Error:[/] Unable to reconstruct state at tick {tick_to_reconstruct} (no preceding snapshot found)."
        )
        raise typer.Exit(code=1)

    console.print(
        f"[bold green]✔ State reconstructed successfully at Day {reconstructed_state.clock.current_tick}![/]"
    )

    # Parity verification against authoritative snapshot if one exists at that tick
    parity_str = "Not verified (no snapshot at target tick)"
    parity_ok = True
    discrepancies: list[str] = []

    if verify:
        snap = store.get_snapshot_at_tick(run_id, tick_to_reconstruct)
        if snap and "state_blob" in snap:
            authoritative_state = deserialize_world_state(snap["state_blob"])
            parity_ok, discrepancies = verify_replay_determinism(
                reconstructed_state, authoritative_state
            )
            if parity_ok:
                parity_str = (
                    "[bold green]✔ 100% Bit-for-Bit Determinism Parity Verified[/]"
                )
            else:
                parity_str = f"[bold red]✘ Discrepancies Detected ({len(discrepancies)} diffs)[/]"
        else:
            parity_str = (
                "[yellow]Snapshot absent at exact tick (event fold validated)[/]"
            )

    # Output Replay Summary Table
    m = reconstructed_state.metrics
    table = Table(box=None, expand=True)
    table.add_column("Replay Diagnostic", style="bold cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Run Identifier", run_id)
    table.add_row("Reconstructed Day", f"Day {reconstructed_state.clock.current_tick}")
    table.add_row(
        "Events Folded",
        f"{len([e for e in all_events if e.tick <= tick_to_reconstruct]):,} events",
    )
    table.add_row("Living Citizens", f"{m.alive_population} agents")
    table.add_row("Reconstructed GDP", f"{m.gdp:,.2f} C")
    table.add_row("Reconstructed CPI", f"{m.cpi:.2f}")
    table.add_row("Treasury Balance", f"{m.treasury_balance:,.2f} C")
    table.add_row("Approval Rating", f"{m.approval_rating:.1f}%")
    table.add_row("Society Harmony", f"{m.society_harmony_index * 100:.1f}%")
    table.add_row("Determinism Parity", parity_str)

    panel = Panel(
        table,
        title=f"[bold green]⏪ Time-Travel Event Replay Summary: Day {tick_to_reconstruct}[/]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(panel)

    if discrepancies:
        console.print("[bold red]Discrepancy Details:[/]")
        for d in discrepancies[:5]:
            console.print(f" • [red]{d}[/]")
