"""HIVEMIND `export` Command (Phase 9).

Exports simulation run events, snapshots, and metrics to JSON or CSV for external analysis.
"""

import csv
import json
import os
from typing import Any

import typer
from rich.console import Console

from backend.events.event_store import EventStore
from backend.persistence.db import create_db_engine_and_factory

console = Console()


def export_command(
    run_id: str = typer.Argument(..., help="Simulation run ID to export."),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (defaults to <run_id>_export.<fmt>).",
    ),
    format_type: str = typer.Option(
        "json", "--format", "-f", help="Export format: 'json' or 'csv'."
    ),
    include_events: bool = typer.Option(
        True, "--include-events/--no-events", help="Include full event log."
    ),
    database_url: str = typer.Option(
        "sqlite:///hivemind.db",
        "--database-url",
        "--db",
        help="Database connection URL.",
    ),
) -> None:
    """Export simulation run events, telemetry, and snapshots to JSON or CSV."""
    _, factory = create_db_engine_and_factory(database_url)
    store = EventStore(factory)
    run_meta = store.get_run(run_id)

    if not run_meta:
        console.print(f"[bold red]Error:[/] Run '{run_id}' not found in database.")
        raise typer.Exit(code=1)

    fmt = format_type.lower()
    if fmt not in ("json", "csv"):
        console.print(
            f"[bold red]Error:[/] Unsupported format '{fmt}'. Choose 'json' or 'csv'."
        )
        raise typer.Exit(code=1)

    out_path = output or f"{run_id}_export.{fmt}"
    events = store.get_events(run_id) if include_events else []
    snapshots = store.get_all_snapshots(run_id)

    console.print(
        f"[bold cyan]Exporting run '{run_id}' to {fmt.upper()} at '{out_path}'...[/]"
    )

    if fmt == "json":
        data: dict[str, Any] = {
            "metadata": run_meta,
            "snapshots_count": len(snapshots),
            "snapshots": [
                {
                    "snapshot_id": s["snapshot_id"],
                    "tick": s["tick"],
                    "metrics": s.get("state_blob", {}).get("metrics", {}),
                }
                for s in snapshots
            ],
            "events_count": len(events),
            "events": [e.to_dict() for e in events],
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    elif fmt == "csv":
        # Extract DayTicked daily metrics for clean tabular CSV export
        day_metrics = []
        for e in events:
            if e.event_type == "DayTicked" and "metrics" in e.payload:
                row = {"tick": e.tick}
                row.update(e.payload["metrics"])
                day_metrics.append(row)

        if not day_metrics and snapshots:
            # Fallback to snapshots metrics if DayTicked events absent
            for s in snapshots:
                row = {"tick": s["tick"]}
                row.update(s.get("state_blob", {}).get("metrics", {}))
                day_metrics.append(row)

        if not day_metrics:
            console.print("[yellow]Warning:[/] No metrics rows found to export to CSV.")
            return

        keys = list(day_metrics[0].keys())
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(day_metrics)

    size_kb = os.path.getsize(out_path) / 1024.0
    console.print(
        f"[bold green]✔ Export complete:[/] [bold white]{out_path}[/] "
        f"({size_kb:.1f} KB, {len(events)} events, {len(snapshots)} snapshots)"
    )
