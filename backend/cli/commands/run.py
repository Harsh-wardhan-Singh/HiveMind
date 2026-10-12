"""HIVEMIND `run` Command (Phase 9).

Executes an interactive or headless simulation with live dashboard updates,
tracking major decisions and displaying LLM / Math Fallback status.
"""

import time
import uuid

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from backend.app.config import CityConfig, SimulationConfig
from backend.cli.ui import render_dashboard
from backend.events.event_types import Event
from backend.simulation.engine import SimulationEngine

console = Console()

SPEED_DELAYS = {
    "slow": 0.30,
    "normal": 0.08,
    "fast": 0.01,
    "max": 0.0,
}


def run_command(
    days: int = typer.Option(
        365, "--days", "-d", help="Total simulation days to advance."
    ),
    population: int = typer.Option(
        100, "--population", "-p", help="Starting citizen population count."
    ),
    seed: int = typer.Option(
        424242, "--seed", "-s", help="Master PRNG determinism seed."
    ),
    speed: str = typer.Option(
        "normal", "--speed", help="Execution speed: 'slow', 'normal', 'fast', 'max'."
    ),
    llm: bool = typer.Option(
        False,
        "--llm/--no-llm",
        help="Enable local Ollama LLM for strategic societal decisions.",
    ),
    llm_model: str = typer.Option(
        "qwen2.5:1.5b", "--llm-model", help="Local Ollama model identifier."
    ),
    llm_base_url: str = typer.Option(
        "http://127.0.0.1:11434", "--llm-base-url", help="Ollama API endpoint URL."
    ),
    step: bool = typer.Option(
        False,
        "--step",
        help="Turn-by-turn stepping mode: pause after every day until Enter is pressed.",
    ),
    headless: bool = typer.Option(
        False, "--headless", help="Run without the live terminal dashboard."
    ),
    database_url: str = typer.Option(
        "sqlite:///hivemind.db",
        "--database-url",
        "--db",
        help="SQLAlchemy database connection URL.",
    ),
    run_id: str | None = typer.Option(
        None, "--run-id", help="Unique identifier for this simulation run."
    ),
    name: str = typer.Option(
        "Hivemind City", "--name", help="Name of the municipal city."
    ),
) -> None:
    """Execute a full HIVEMIND simulation run with live terminal visualization."""
    actual_run_id = run_id or f"run_{uuid.uuid4().hex[:8]}"
    delay = SPEED_DELAYS.get(speed.lower(), 0.08)

    config = SimulationConfig(
        run_id=actual_run_id,
        seed=seed,
        total_days=days,
        snapshot_interval_days=30,
        database_url=database_url,
        llm_enabled=llm,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        city=CityConfig(
            name=name,
            starting_population=population,
        ),
    )

    console.print(
        f"[bold cyan]Initializing HIVEMIND simulation engine...[/] (Run: [bold white]{actual_run_id}[/], Seed: [bold]{seed}[/])"
    )

    with SimulationEngine(config) as engine:
        recent_events: list[Event] = []
        start_time = time.time()
        was_interrupted = False

        if headless:
            console.print(
                f"[bold green]▶ Running Headless[/] | Days: {days} | Pop: {population} | "
                f"LLM: {'Active (' + llm_model + ')' if llm else '100% Math Fallback'}"
            )
            try:
                for tick in range(1, days + 1):
                    day_events = engine.step()
                    recent_events.extend(day_events)

                    # Print progress every 30 days or on key societal events
                    has_major_event = any(
                        e.event_type
                        in (
                            "StrategicDecisionMade",
                            "RiotStarted",
                            "ElectionHeld",
                            "CorruptionScandalExposed",
                        )
                        for e in day_events
                    )
                    if tick % 30 == 0 or tick == days or has_major_event:
                        m = engine.state.metrics
                        console.print(
                            f" Day {tick:03d}/{days} | Pop: {m.alive_population:3d} | "
                            f"Treasury: {m.treasury_balance:8.1f} C | CPI: {m.cpi:5.2f} | "
                            f"Approv: {m.approval_rating:5.1f}% | Unrest: {m.city_unrest:.2f} | "
                            f"Harmony: {m.society_harmony_index * 100:.0f}%"
                        )
            except KeyboardInterrupt:
                was_interrupted = True
                console.print(
                    "\n[bold yellow]⚠️ Execution paused by operator (Ctrl+C). Saving point-in-time state...[/]"
                )
        elif step:
            # Turn-by-turn interactive stepping mode
            console.print(
                "[bold cyan]▶ Running Turn-by-Turn Stepping Mode. Press [Enter] each day, or 'q' to pause & take action.[/]"
            )
            try:
                for _ in range(1, days + 1):
                    day_events = engine.step()
                    recent_events.extend(day_events)
                    if len(recent_events) > 100:
                        recent_events = recent_events[-60:]

                    dashboard = render_dashboard(
                        state=engine.state,
                        recent_events=recent_events,
                        run_id=actual_run_id,
                        total_days=days,
                        speed_name="STEP",
                    )
                    console.print(dashboard)

                    user_input = console.input(
                        f"[bold yellow]⏸️  Day {engine.state.clock.current_tick} completed. Press [Enter] for next day, 'c' to run continuous, or 'q' to pause & take action: [/]"
                    )
                    cmd = user_input.strip().lower()
                    if cmd == "q":
                        was_interrupted = True
                        break
                    elif cmd == "c":
                        step = False
            except KeyboardInterrupt:
                was_interrupted = True
                console.print(
                    "\n[bold yellow]⚠️ Stepping paused by operator (Ctrl+C). Saving point-in-time state...[/]"
                )
        else:
            # Interactive Rich Live Dashboard
            initial_layout = render_dashboard(
                state=engine.state,
                recent_events=recent_events,
                run_id=actual_run_id,
                total_days=days,
                speed_name=speed.upper(),
            )

            try:
                with Live(initial_layout, refresh_per_second=15, screen=False) as live:
                    for _ in range(1, days + 1):
                        day_events = engine.step()
                        recent_events.extend(day_events)

                        # Keep the recent events buffer bounded
                        if len(recent_events) > 100:
                            recent_events = recent_events[-60:]

                        dashboard = render_dashboard(
                            state=engine.state,
                            recent_events=recent_events,
                            run_id=actual_run_id,
                            total_days=days,
                            speed_name=speed.upper(),
                        )
                        live.update(dashboard)

                        if delay > 0:
                            time.sleep(delay)
            except KeyboardInterrupt:
                was_interrupted = True
                console.print(
                    "\n[bold yellow]⚠️ Execution paused by operator (Ctrl+C). Saving point-in-time state...[/]"
                )

        elapsed = time.time() - start_time
        fps = engine.state.clock.current_tick / elapsed if elapsed > 0 else 0.0

        # Persist authoritative state snapshot
        snap_id = engine.save_snapshot()
        current_tick = engine.state.clock.current_tick

        # Display Run Summary Card
        m = engine.state.metrics
        summary_table = Table(box=None, expand=True)
        summary_table.add_column("Attribute", style="bold cyan")
        summary_table.add_column("Value", style="bold white")

        summary_table.add_row("Run Identifier", actual_run_id)
        summary_table.add_row("City Name", name)
        summary_table.add_row("Total Days Completed", f"{current_tick} of {days}")
        summary_table.add_row(
            "Elapsed Wall-Clock Time", f"{elapsed:.2f} seconds ({fps:.1f} days/sec)"
        )
        summary_table.add_row(
            "Living Citizens", f"{m.alive_population} / {m.total_population}"
        )
        summary_table.add_row("Gross Domestic Product (GDP)", f"{m.gdp:,.2f} C")
        summary_table.add_row(
            "Consumer Price Index (CPI)",
            f"{m.cpi:.2f} (Inflation: {m.inflation_rate:+.1f}%)",
        )
        summary_table.add_row(
            "Municipal Treasury Balance", f"{m.treasury_balance:,.2f} C"
        )
        summary_table.add_row("Citizen Approval Rating", f"{m.approval_rating:.1f}%")
        summary_table.add_row("Civil Unrest Score", f"{m.city_unrest:.2f}")
        summary_table.add_row(
            "Society Harmony Index", f"{m.society_harmony_index * 100:.1f}%"
        )
        summary_table.add_row("Authoritative Snapshot Saved", snap_id)

        # Strategic Decisions Breakdown
        gw = engine.state.llm_gateway
        model_name = getattr(gw, "model_name", "qwen2.5:1.5b")
        mode_str = (
            f"[bold green]LLM Active ({model_name})[/] ({gw.llm_decisions} decisions, {gw.fallback_decisions} fallbacks)"
            if getattr(gw, "enabled", False)
            else f"[bold yellow]100% Mathematical Fallback[/] ({gw.fallback_decisions} decisions)"
        )
        summary_table.add_row("Decision Governance Mode", mode_str)

        summary_panel = Panel(
            summary_table,
            title=(
                "[bold yellow]⏸️ SIMULATION PAUSED BY OPERATOR — STATE SNAPSHOT CAPTURED[/]"
                if was_interrupted
                else "[bold green]🏆 SIMULATION RUN COMPLETE — EXECUTIVE SUMMARY[/]"
            ),
            border_style="yellow" if was_interrupted else "green",
            padding=(1, 2),
        )
        console.print("\n", summary_panel)

        if was_interrupted:
            action_card = Table.grid(expand=True)
            action_card.add_column()
            action_card.add_row(
                f"[bold yellow]⏸️ Simulation paused at Day {current_tick} of {days}[/] (Run ID: [bold cyan]{actual_run_id}[/])\n"
                f"Authoritative point-in-time snapshot saved: [bold green]{snap_id}[/]\n"
            )
            action_card.add_row(
                "[bold white]Here is how you can inspect what happened and take action right now:[/]\n"
            )
            action_card.add_row(
                " [bold cyan]1. INSPECT THE CURRENT STATE[/]\n"
                f"    [white]python cli.py inspect run {actual_run_id}[/]                    [dim]# City overview & indicators[/]\n"
                f"    [white]python cli.py inspect events {actual_run_id} --limit 15[/]        [dim]# Recent decisions & crises[/]\n"
                f"    [white]python cli.py inspect district dist_industrial[/]               [dim]# Inspect district unrest[/]\n"
            )
            action_card.add_row(
                " [bold cyan]2. TAKE ACTION & INTERVENE (Fork timeline with emergency policies)[/]\n"
                f"    [dim]# Enact Food Subsidy to reduce living costs and lower unrest:[/]\n"
                f"    [bold green]python cli.py branch {actual_run_id} --tick {current_tick} --subsidy 0.30 --days 30[/]\n\n"
                f"    [dim]# Enact Fiscal Austerity & Corporate Tax reform to balance treasury:[/]\n"
                f"    [bold green]python cli.py branch {actual_run_id} --tick {current_tick} --austerity 0.20 --corp-tax 0.25 --days 30[/]\n\n"
                f"    [dim]# Inject Emergency Municipal Grant liquidity into City Hall:[/]\n"
                f"    [bold green]python cli.py branch {actual_run_id} --tick {current_tick} --grant 20000 --days 30[/]\n"
            )
            action_card.add_row(
                " [bold cyan]3. RESUME SIMULATION FORWARD[/]\n"
                f"    [white]python cli.py branch {actual_run_id} --tick {current_tick} --name 'Resumed Run' --days {max(days - current_tick, 30)}[/]\n"
            )
            action_card.add_row(
                " [bold cyan]4. EXPORT DATA FOR ANALYSIS[/]\n"
                f"    [white]python cli.py export {actual_run_id} --format json[/]\n"
            )

            console.print(
                Panel(
                    action_card,
                    title="[bold yellow]🎮 OPERATOR INTERVENTION & ACTION MENU[/]",
                    border_style="yellow",
                    padding=(1, 2),
                )
            )
        else:
            next_steps = Table.grid(expand=True)
            next_steps.add_column()
            next_steps.add_row(
                f"[bold cyan]👉 Simulation Run Completed Successfully![/]\n\n"
                f" • [bold white]Inspect full run:[/]      python cli.py inspect run {actual_run_id}\n"
                f" • [bold white]Inspect event log:[/]     python cli.py inspect events {actual_run_id} --limit 20\n"
                f" • [bold white]Fork counterfactual:[/]   python cli.py branch {actual_run_id} --tick {current_tick // 2} --subsidy 0.30\n"
                f" • [bold white]Export to JSON/CSV:[/]    python cli.py export {actual_run_id} --format json\n"
            )
            console.print(
                Panel(
                    next_steps,
                    title="[bold cyan]💡 NEXT STEPS & EXPLORATION[/]",
                    border_style="cyan",
                    padding=(1, 2),
                )
            )
