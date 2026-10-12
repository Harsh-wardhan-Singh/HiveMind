"""HIVEMIND Master CLI Entry Point (Phase 9).

Orchestrates all CLI operations: run, inspect, branch, replay, compare, and export.
"""

import typer
from rich.console import Console

from backend.cli.commands.branch import branch_command
from backend.cli.commands.compare import compare_command
from backend.cli.commands.export import export_command
from backend.cli.commands.inspect import inspect_app
from backend.cli.commands.replay import replay_command
from backend.cli.commands.run import run_command

console = Console()
app = typer.Typer(
    name="hivemind",
    help="🏛️ HIVEMIND: Multi-Agent Societal Simulation & Macroeconomic Policy Lab",
    add_completion=False,
    no_args_is_help=True,
)

# Register top-level commands
app.command(name="run", help="Launch an interactive or headless simulation run.")(
    run_command
)
app.add_typer(inspect_app, name="inspect")
app.command(
    name="branch",
    help="Fork an existing simulation timeline with counterfactual policies.",
)(branch_command)
app.command(
    name="replay", help="Replay historical event streams and verify determinism parity."
)(replay_command)
app.command(
    name="compare",
    help="Compare longitudinal trajectories and compute metric divergence.",
)(compare_command)
app.command(
    name="export", help="Export events, telemetry, and snapshots to JSON or CSV."
)(export_command)


def version_callback(value: bool):
    if value:
        console.print(
            "[bold cyan]HIVEMIND[/] version [bold white]1.0.0[/] (Phase 9 Operator CLI)"
        )
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="Show HIVEMIND version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
):
    """HIVEMIND — Autonomous Macroeconomic & Civic Policy Simulation Engine."""


if __name__ == "__main__":
    app()
