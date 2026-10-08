"""HIVEMIND Differential Trajectory Analytics Engine (Phase 8).

Computes point-in-time and longitudinal metric divergence between two simulation runs
(e.g., comparing counterfactual branch trajectories against parent baselines).
"""

from dataclasses import dataclass, field
from typing import Any

from backend.events.event_store import EventStore


@dataclass
class MetricDelta:
    """Point-in-time comparative delta for a single metric."""

    metric_name: str
    tick: int
    val_a: float
    val_b: float
    diff: float
    pct_diff: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "tick": self.tick,
            "val_a": round(self.val_a, 4),
            "val_b": round(self.val_b, 4),
            "diff": round(self.diff, 4),
            "pct_diff": round(self.pct_diff, 2),
        }


@dataclass
class TrajectoryMetricSummary:
    """Longitudinal divergence summary for a specific metric across the comparison window."""

    metric_name: str
    mean_val_a: float
    mean_val_b: float
    final_val_a: float
    final_val_b: float
    final_diff: float
    final_pct_diff: float
    max_divergence: float
    max_divergence_tick: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "mean_val_a": round(self.mean_val_a, 4),
            "mean_val_b": round(self.mean_val_b, 4),
            "final_val_a": round(self.final_val_a, 4),
            "final_val_b": round(self.final_val_b, 4),
            "final_diff": round(self.final_diff, 4),
            "final_pct_diff": round(self.final_pct_diff, 2),
            "max_divergence": round(self.max_divergence, 4),
            "max_divergence_tick": self.max_divergence_tick,
        }


@dataclass
class DifferentialTrajectoryAnalysis:
    """Complete comparative analysis of two simulation trajectories."""

    run_id_a: str
    run_id_b: str
    name_a: str
    name_b: str
    fork_tick: int | None
    start_tick: int
    end_tick: int
    ticks_compared: int
    metrics_compared: list[str]
    daily_deltas: dict[str, list[MetricDelta]] = field(default_factory=dict)
    summaries: dict[str, TrajectoryMetricSummary] = field(default_factory=dict)
    qualitative_verdict: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id_a": self.run_id_a,
            "run_id_b": self.run_id_b,
            "name_a": self.name_a,
            "name_b": self.name_b,
            "fork_tick": self.fork_tick,
            "start_tick": self.start_tick,
            "end_tick": self.end_tick,
            "ticks_compared": self.ticks_compared,
            "metrics_compared": self.metrics_compared,
            "summaries": {k: v.to_dict() for k, v in self.summaries.items()},
            "qualitative_verdict": self.qualitative_verdict,
        }


DEFAULT_METRICS_TO_COMPARE = [
    "treasury_balance",
    "gdp",
    "cpi",
    "approval_rating",
    "city_unrest",
    "society_harmony_index",
    "alive_population",
    "unemployment_rate",
    "average_health",
]


def compare_simulation_runs(
    event_store: EventStore,
    run_id_a: str,
    run_id_b: str,
    metrics: list[str] | None = None,
) -> DifferentialTrajectoryAnalysis:
    """
    Compare chronological trajectories of run_id_a and run_id_b.
    Identifies common ticks, calculates deltas, and produces divergence statistics.
    """
    target_metrics = metrics or DEFAULT_METRICS_TO_COMPARE

    # Fetch run metadata
    run_a_meta = event_store.get_run(run_id_a) or {}
    run_b_meta = event_store.get_run(run_id_b) or {}
    name_a = run_a_meta.get("name") or run_id_a
    name_b = run_b_meta.get("name") or run_id_b
    fork_tick = run_b_meta.get("fork_tick") or run_a_meta.get("fork_tick")

    # Fetch DayTicked events
    events_a = event_store.get_events(run_id_a)
    events_b = event_store.get_events(run_id_b)

    days_a: dict[int, dict[str, Any]] = {}
    for e in events_a:
        if e.event_type == "DayTicked" and "metrics" in e.payload:
            days_a[e.tick] = e.payload["metrics"]

    days_b: dict[int, dict[str, Any]] = {}
    for e in events_b:
        if e.event_type == "DayTicked" and "metrics" in e.payload:
            days_b[e.tick] = e.payload["metrics"]

    # If fork_tick is present, ensure fork_tick baseline metrics are populated for branches
    if fork_tick is not None:
        if fork_tick not in days_a:
            snap_a = event_store.get_snapshot_at_tick(run_id_a, fork_tick)
            if snap_a and "state_blob" in snap_a and "metrics" in snap_a["state_blob"]:
                days_a[fork_tick] = snap_a["state_blob"]["metrics"]
            elif fork_tick in days_b:
                days_a[fork_tick] = days_b[fork_tick]
            elif run_a_meta.get("parent_run_id"):
                p_snap = event_store.get_snapshot_at_tick(
                    run_a_meta["parent_run_id"], fork_tick
                )
                if (
                    p_snap
                    and "state_blob" in p_snap
                    and "metrics" in p_snap["state_blob"]
                ):
                    days_a[fork_tick] = p_snap["state_blob"]["metrics"]

        if fork_tick not in days_b:
            snap_b = event_store.get_snapshot_at_tick(run_id_b, fork_tick)
            if snap_b and "state_blob" in snap_b and "metrics" in snap_b["state_blob"]:
                days_b[fork_tick] = snap_b["state_blob"]["metrics"]
            elif fork_tick in days_a:
                days_b[fork_tick] = days_a[fork_tick]
            elif run_b_meta.get("parent_run_id"):
                p_snap = event_store.get_snapshot_at_tick(
                    run_b_meta["parent_run_id"], fork_tick
                )
                if (
                    p_snap
                    and "state_blob" in p_snap
                    and "metrics" in p_snap["state_blob"]
                ):
                    days_b[fork_tick] = p_snap["state_blob"]["metrics"]

    # If run_b is a branch starting from fork_tick, compare from fork_tick forward
    start_tick = (
        fork_tick
        if fork_tick is not None and (fork_tick in days_a or fork_tick in days_b)
        else 1
    )
    common_ticks = sorted(set(days_a.keys()).intersection(set(days_b.keys())))
    common_ticks = [t for t in common_ticks if t >= start_tick]

    if not common_ticks:
        # If no common ticks directly match, use all available ticks for both
        start_tick = min(days_a.keys(), default=0)
        end_tick = max(days_a.keys(), default=0)
        return DifferentialTrajectoryAnalysis(
            run_id_a=run_id_a,
            run_id_b=run_id_b,
            name_a=name_a,
            name_b=name_b,
            fork_tick=fork_tick,
            start_tick=start_tick,
            end_tick=end_tick,
            ticks_compared=0,
            metrics_compared=target_metrics,
            qualitative_verdict="No overlapping ticks found to compare.",
        )

    end_tick = max(common_ticks)

    daily_deltas: dict[str, list[MetricDelta]] = {m: [] for m in target_metrics}
    summaries: dict[str, TrajectoryMetricSummary] = {}

    for m in target_metrics:
        vals_a: list[float] = []
        vals_b: list[float] = []
        max_div = 0.0
        max_div_tick = common_ticks[0]

        for t in common_ticks:
            va = float(days_a[t].get(m, 0.0))
            vb = float(days_b[t].get(m, 0.0))
            vals_a.append(va)
            vals_b.append(vb)

            diff = vb - va
            pct_diff = (diff / va * 100.0) if abs(va) > 1e-6 else 0.0

            delta = MetricDelta(
                metric_name=m,
                tick=t,
                val_a=va,
                val_b=vb,
                diff=diff,
                pct_diff=pct_diff,
            )
            daily_deltas[m].append(delta)

            if abs(diff) > abs(max_div):
                max_div = diff
                max_div_tick = t

        final_va = vals_a[-1]
        final_vb = vals_b[-1]
        final_diff = final_vb - final_va
        final_pct_diff = (
            (final_diff / final_va * 100.0) if abs(final_va) > 1e-6 else 0.0
        )

        summaries[m] = TrajectoryMetricSummary(
            metric_name=m,
            mean_val_a=sum(vals_a) / len(vals_a),
            mean_val_b=sum(vals_b) / len(vals_b),
            final_val_a=final_va,
            final_val_b=final_vb,
            final_diff=final_diff,
            final_pct_diff=final_pct_diff,
            max_divergence=max_div,
            max_divergence_tick=max_div_tick,
        )

    # Formulate qualitative impact verdict
    verdicts = []
    if "approval_rating" in summaries:
        app_sum = summaries["approval_rating"]
        if app_sum.final_diff > 2.0:
            verdicts.append(f"Approval improved by +{app_sum.final_diff:.1f}%")
        elif app_sum.final_diff < -2.0:
            verdicts.append(f"Approval dropped by {app_sum.final_diff:.1f}%")

    if "treasury_balance" in summaries:
        tr_sum = summaries["treasury_balance"]
        if tr_sum.final_diff > 100.0:
            verdicts.append(f"Treasury expanded by +{tr_sum.final_diff:,.1f} C")
        elif tr_sum.final_diff < -100.0:
            verdicts.append(f"Treasury depleted by {tr_sum.final_diff:,.1f} C")

    if "city_unrest" in summaries:
        unr_sum = summaries["city_unrest"]
        if unr_sum.final_diff > 0.05:
            verdicts.append(f"Civil unrest elevated (+{unr_sum.final_diff:.2f})")
        elif unr_sum.final_diff < -0.05:
            verdicts.append(f"Civil unrest pacified ({unr_sum.final_diff:.2f})")

    qualitative_verdict = (
        "; ".join(verdicts)
        if verdicts
        else "Trajectories exhibited negligible divergence."
    )

    return DifferentialTrajectoryAnalysis(
        run_id_a=run_id_a,
        run_id_b=run_id_b,
        name_a=name_a,
        name_b=name_b,
        fork_tick=fork_tick,
        start_tick=common_ticks[0],
        end_tick=end_tick,
        ticks_compared=len(common_ticks),
        metrics_compared=target_metrics,
        daily_deltas=daily_deltas,
        summaries=summaries,
        qualitative_verdict=qualitative_verdict,
    )


def generate_ascii_delta_table(analysis: DifferentialTrajectoryAnalysis) -> str:
    """
    Format a clean ASCII comparative matrix table for CLI or markdown reports.
    """
    lines = [
        "=" * 92,
        f" DIFFERENTIAL TRAJECTORY COMPARISON: {analysis.name_a} vs {analysis.name_b}",
        f" Run A: {analysis.run_id_a} | Run B: {analysis.run_id_b} | Fork Tick: {analysis.fork_tick}",
        f" Window: Day {analysis.start_tick} -> Day {analysis.end_tick} ({analysis.ticks_compared} days compared)",
        "=" * 92,
        f"{'Metric':<25} | {'Baseline (A)':<14} | {'Branch (B)':<14} | {'Terminal Delta':<14} | {'Delta %':<10}",
        "-" * 92,
    ]

    for m, s in analysis.summaries.items():
        delta_str = f"{s.final_diff:+.2f}"
        pct_str = f"{s.final_pct_diff:+.1f}%"
        lines.append(
            f"{m:<25} | {s.final_val_a:14.2f} | {s.final_val_b:14.2f} | {delta_str:14} | {pct_str:10}"
        )

    lines.append("-" * 92)
    lines.append(f" Qualitative Verdict: {analysis.qualitative_verdict}")
    lines.append("=" * 92)
    return "\n".join(lines)


def generate_comparison_chart_data(
    analysis: DifferentialTrajectoryAnalysis,
) -> dict[str, Any]:
    """
    Produce JSON-serializable multi-line time series data for Web UI charts in Phase 10.
    """
    chart_series: dict[str, list[dict[str, Any]]] = {}

    for metric_name, deltas in analysis.daily_deltas.items():
        chart_series[metric_name] = [
            {
                "tick": d.tick,
                "baseline": d.val_a,
                "branch": d.val_b,
                "delta": d.diff,
            }
            for d in deltas
        ]

    return {
        "run_id_a": analysis.run_id_a,
        "run_id_b": analysis.run_id_b,
        "fork_tick": analysis.fork_tick,
        "start_tick": analysis.start_tick,
        "end_tick": analysis.end_tick,
        "series": chart_series,
        "summaries": {k: v.to_dict() for k, v in analysis.summaries.items()},
        "verdict": analysis.qualitative_verdict,
    }
