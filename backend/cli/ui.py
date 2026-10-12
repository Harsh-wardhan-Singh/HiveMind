"""HIVEMIND Terminal User Interface (TUI) & Rich Dashboard Module (Phase 9).

Provides a live updating multi-panel terminal dashboard, color-coded metric tables,
and a scrolling event feed tracking every major societal decision.
"""

from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from backend.events.event_types import Event
from backend.simulation.state import WorldState


def build_header_panel(
    run_id: str,
    tick: int,
    total_days: int,
    date_str: str,
    speed_name: str,
    llm_enabled: bool,
    llm_model: str,
) -> Panel:
    """Construct top header banner with simulation status and LLM Indicator Badge."""
    grid = Table.grid(expand=True)
    grid.add_column(justify="left", ratio=3)
    grid.add_column(justify="center", ratio=4)
    grid.add_column(justify="right", ratio=3)

    # Title & Run ID
    title_text = Text()
    title_text.append("🏛️  HIVEMIND ", style="bold cyan")
    title_text.append(f"[{run_id}]", style="dim white")

    # Time & Progress
    time_text = Text()
    progress_pct = (tick / total_days * 100.0) if total_days > 0 else 0.0
    time_text.append(f"Day {tick:03d} / {total_days}", style="bold white")
    time_text.append(f" ({progress_pct:.0f}%)", style="cyan")
    time_text.append(f"  •  {date_str}", style="bright_yellow")
    time_text.append(f"  •  Speed: {speed_name}", style="dim")

    # LLM Status Indicator Badge (Prompt requirement: explicit badge for LLM vs Math Fallback)
    llm_badge = Text()
    if llm_enabled:
        llm_badge.append("● LLM REASONING: ", style="bold green")
        llm_badge.append(f"{llm_model}", style="bold cyan")
    else:
        llm_badge.append("○ 100% MATH FALLBACK", style="bold yellow")
        llm_badge.append(" (deterministic)", style="dim")

    grid.add_row(title_text, time_text, llm_badge)

    return Panel(
        grid,
        style="bright_blue",
        padding=(0, 1),
    )


def build_macro_panel(state: WorldState) -> Panel:
    """Format macroeconomic indicators, corporate health, and municipal banking."""
    m = state.metrics
    gov = state.government
    bank = state.bank

    table = Table(box=None, expand=True, padding=(0, 1))
    table.add_column("Macro Indicator", style="dim white", ratio=4)
    table.add_column("Value", justify="right", style="bold white", ratio=3)

    # Macro & Pricing
    table.add_row("City GDP (daily)", f"{m.gdp:,.2f} C")
    table.add_row("Laspeyres CPI", f"{m.cpi:.2f}")
    cpi_color = (
        "red"
        if m.inflation_rate > 5.0
        else ("green" if m.inflation_rate >= 0 else "yellow")
    )
    table.add_row("Inflation Rate (30d)", f"[{cpi_color}]{m.inflation_rate:+.1f}%[/]")
    table.add_row("Unemployment Rate", f"{m.unemployment_rate * 100:.1f}%")
    table.add_row("Average Daily Wage", f"{m.average_wage:.2f} C")
    solvent_cnt = sum(
        1 for c in state.companies.values() if getattr(c, "solvency", True)
    )
    total_comps = len(state.companies)
    table.add_row("Corporate Solvency", f"{solvent_cnt}/{total_comps} active")

    table.add_section()

    # Municipal Treasury & Public Finances
    table.add_row("Municipal Treasury", f"[bold green]{gov.treasury:,.1f} C[/]")
    table.add_row("Daily Tax Revenue", f"+{gov.daily_tax_revenue:,.1f} C")
    table.add_row("Daily Expenditures", f"-{gov.daily_expenditures:,.1f} C")

    table.add_section()

    # Banking & Equities
    table.add_row("Bank Total Deposits", f"{bank.total_deposits:,.1f} C")
    table.add_row("Bank Total Loans", f"{bank.total_loans:,.1f} C")
    table.add_row("Bank Cash Reserves", f"{bank.cash_reserves:,.1f} C")
    table.add_row("Stock Market Cap", f"{m.stock_market_cap:,.0f} C")

    return Panel(
        table,
        title="[bold cyan]📊 Macroeconomics & Capital Markets[/]",
        border_style="cyan",
        padding=(0, 1),
    )


def build_demographics_panel(state: WorldState) -> Panel:
    """Format societal demographics, public health, and social ecology."""
    m = state.metrics
    harm = state.harmony_tracker

    table = Table(box=None, expand=True, padding=(0, 1))
    table.add_column("Societal Metric", style="dim white", ratio=4)
    table.add_column("Status", justify="right", style="bold white", ratio=3)

    # Demographics
    table.add_row("Citizen Population", f"{m.alive_population} alive")
    deceased = m.total_population - m.alive_population
    dec_color = "red" if deceased > 0 else "dim"
    table.add_row("Deceased Citizens", f"[{dec_color}]{deceased}[/]")
    table.add_row("Active Households", f"{len(state.households)}")

    # Health
    health_pct = m.average_health * 100.0
    h_color = "green" if health_pct > 80 else ("yellow" if health_pct > 60 else "red")
    table.add_row("Average Health", f"[{h_color}]{health_pct:.1f}%[/]")

    table.add_section()

    # Information Ecology & Harmony
    harm_pct = harm.harmony_index * 100.0
    harm_color = (
        "green" if harm_pct > 70 else ("yellow" if harm_pct > 40 else "bold red")
    )
    table.add_row("Society Harmony", f"[{harm_color}]{harm_pct:.1f}%[/]")

    distrust_pct = harm.interpersonal_distrust * 100.0
    d_color = (
        "red" if distrust_pct > 30 else ("yellow" if distrust_pct > 15 else "green")
    )
    table.add_row("Interpersonal Distrust", f"[{d_color}]{distrust_pct:.1f}%[/]")

    table.add_row("Mean Social Trust", f"{m.mean_social_trust:.2f}")
    table.add_row("Active Rumors", f"{len(state.rumor_engine.active_rumors)}")
    table.add_row(
        "Media Press Archive", f"{len(state.media_engine.articles_archive)} articles"
    )

    table.add_section()

    # LLM Telemetry
    gw = state.llm_gateway
    table.add_row("Total Strategic Decisions", f"{gw.total_decisions}")
    llm_dec_str = f"[bold green]{gw.llm_decisions}[/]" if gw.llm_decisions > 0 else "0"
    table.add_row("Decided by LLM", llm_dec_str)
    fb_dec_str = (
        f"[bold yellow]{gw.fallback_decisions}[/]" if gw.fallback_decisions > 0 else "0"
    )
    table.add_row("Decided by Math Fallback", fb_dec_str)

    return Panel(
        table,
        title="[bold green]👥 Demographics & Information Ecology[/]",
        border_style="green",
        padding=(0, 1),
    )


def build_politics_panel(state: WorldState) -> Panel:
    """Format municipal governance, political stability, unrest, and active policies."""
    m = state.metrics
    gov = state.government

    table = Table(box=None, expand=True, padding=(0, 1))
    table.add_column("Governance Metric", style="dim white", ratio=4)
    table.add_column("Value", justify="right", style="bold white", ratio=3)

    # Mayor & Administration
    mayor_agent = state.agents.get(gov.current_mayor_id)
    mayor_label = f"{gov.current_mayor_id}"
    if mayor_agent:
        mayor_label = f"{mayor_agent.id} ({mayor_agent.role.value})"
    table.add_row("Sitting Mayor", f"[bold white]{mayor_label}[/]")

    appr = m.approval_rating
    appr_color = "green" if appr >= 70 else ("yellow" if appr >= 45 else "bold red")
    table.add_row("Citizen Approval", f"[{appr_color}]{appr:.1f}%[/]")

    fav = m.city_favorability
    fav_color = "green" if fav >= 0.60 else ("yellow" if fav >= 0.35 else "bold red")
    table.add_row("City Favorability Index", f"[{fav_color}]{fav:.2f}[/]")

    table.add_section()

    # Civil Stability & Riots
    unrest = m.city_unrest
    u_color = "red" if unrest > 0.40 else ("yellow" if unrest > 0.20 else "green")
    table.add_row("Civil Unrest Score", f"[{u_color}]{unrest:.2f}[/]")

    riots_cnt = m.rioting_districts_count
    r_color = "bold red" if riots_cnt > 0 else "green"
    table.add_row("Rioting Districts", f"[{r_color}]{riots_cnt} active[/]")

    corr = gov.corruption_index
    corr_color = "bold red" if corr > 0.08 else ("yellow" if corr > 0.03 else "green")
    table.add_row("Corruption Index", f"[{corr_color}]{corr:.4f}[/]")
    table.add_row("Total Embezzled", f"{gov.total_embezzled:,.1f} C")

    table.add_section()

    # Active Policies
    active_pols = state.policy_manager.active_policies
    table.add_row("Active Decrees Count", f"{len(active_pols)}")
    if active_pols:
        for p in list(active_pols.values())[:3]:
            table.add_row(f" • {p.policy_type.value[:14]}", f"mag {p.magnitude:.2f}")
    else:
        table.add_row(" • Standard Laws", "[dim]No emergency decrees[/]")

    return Panel(
        table,
        title="[bold yellow]⚖️ Municipal Governance & Stability[/]",
        border_style="yellow",
        padding=(0, 1),
    )


def format_event_badge_and_text(evt: Event) -> tuple[str, str]:
    """
    Format an immutable event into a high-visibility badge and concise descriptive text
    specifically highlighting major decisions, riots, elections, and news.
    """
    etype = evt.event_type
    p = evt.payload
    tick = evt.tick

    if etype == "StrategicDecisionMade":
        source = p.get("source", "MATH_FALLBACK")
        action = p.get("chosen_action", "NO_ACTION")
        role = p.get("role", "MAYOR")
        badge = (
            "[bold magenta]⚡ LLM DECISION[/]"
            if source == "LLM_REASONING"
            else "[bold yellow]⚙️ MATH FALLBACK[/]"
        )
        rationale = p.get("rationale", "")[:60]
        text = f"Day {tick:03d} | {role} enacted '{action}' -> {rationale}"
        return badge, text

    elif etype == "RiotStarted":
        dist_id = p.get("district_id", "")
        score = p.get("unrest_score", 0.0)
        badge = "[bold white on red]🔥 RIOT STARTED[/]"
        return (
            badge,
            f"Day {tick:03d} | Civil unrest erupted in '{dist_id}' (Unrest: {score:.2f})!",
        )

    elif etype == "RiotQuelled":
        dist_id = p.get("district_id", "")
        badge = "[bold green]🛡️ RIOT QUELLED[/]"
        return (
            badge,
            f"Day {tick:03d} | Order and security restored in district '{dist_id}'.",
        )

    elif etype == "ElectionHeld":
        winner = p.get("winner_name", "Candidate")
        platform = p.get("winner_platform", "General")
        votes = p.get("total_votes_cast", 0)
        badge = "[bold blue]🗳️ ELECTION HELD[/]"
        return (
            badge,
            f"Day {tick:03d} | Election concluded ({votes} ballots). Winner: {winner} [{platform}].",
        )

    elif etype == "MayoralTransition":
        new_m = p.get("new_mayor_name", "")
        platform = p.get("platform", "")
        badge = "[bold cyan]👑 MAYORAL TRANSFER[/]"
        return (
            badge,
            f"Day {tick:03d} | Peaceful transfer of power! New Mayor {new_m} inaugurated ({platform}).",
        )

    elif etype == "CorruptionScandalExposed":
        cor_idx = p.get("corruption_index", 0.0)
        stolen = p.get("total_embezzled", 0.0)
        badge = "[bold white on dark_red]⚠️ SCANDAL EXPOSED[/]"
        return (
            badge,
            f"Day {tick:03d} | Investigative leak exposed City Hall graft! Embezzled: {stolen:,.1f} C (Idx: {cor_idx:.3f}).",
        )

    elif etype == "PolicyEnacted":
        ptype = p.get("policy_type", "")
        mag = p.get("magnitude", 0.0)
        badge = "[bold yellow]📜 POLICY ENACTED[/]"
        return (
            badge,
            f"Day {tick:03d} | Executive decree enacted: {ptype} (magnitude: {mag}).",
        )

    elif etype == "PolicyExpired":
        pid = p.get("policy_id", "")
        badge = "[dim yellow]⌛ POLICY EXPIRED[/]"
        return badge, f"Day {tick:03d} | Emergency policy mandate expired: {pid}."

    elif etype == "TimelineForked":
        b_name = p.get("branch_name", "")
        badge = "[bold purple]🔀 TIMELINE FORKED[/]"
        return (
            badge,
            f"Day {tick:03d} | Timeline branched into counterfactual future: '{b_name}'.",
        )

    elif etype == "NewsPublished":
        outlet = p.get("publisher", "Press")
        hl = p.get("headline", "")
        badge = "[bold white]📰 NEWS BROADCAST[/]"
        return badge, f"Day {tick:03d} | [{outlet}] {hl}"

    elif etype == "RumorSpawned":
        topic = p.get("topic", "")
        hl = p.get("headline", "")
        badge = "[bold italic bright_yellow]🗣️ RUMOR SPAWNED[/]"
        return badge, f"Day {tick:03d} | Hearsay surfaced: '{topic}' - {hl}"

    elif etype == "RumorDiffused":
        trans = p.get("transmissions_count", 0)
        badge = "[italic yellow]💬 RUMOR DIFFUSED[/]"
        return (
            badge,
            f"Day {tick:03d} | Word-of-mouth shared across {trans} social edges.",
        )

    elif etype == "HarmonyShifted":
        h = p.get("harmony_index", 0.0)
        badge = "[dim cyan]🎶 HARMONY SHIFT[/]"
        return (
            badge,
            f"Day {tick:03d} | Society Harmony Index updated to {h * 100:.1f}%.",
        )

    elif etype == "AgentDied":
        a_id = p.get("agent_id", "")
        cause = p.get("cause", "")
        age = p.get("age_years", 0)
        badge = "[dim red]✝ AGENT DIED[/]"
        return (
            badge,
            f"Day {tick:03d} | Citizen {a_id} passed away at age {age} ({cause}).",
        )

    elif etype == "EquityTraded":
        ticker = p.get("ticker", "")
        price = p.get("price", 0.0)
        qty = p.get("quantity", 0)
        badge = "[dim green]📈 EQUITY TRADE[/]"
        return (
            badge,
            f"Day {tick:03d} | Order book matched: {qty} shares of {ticker} @ {price:.2f} C.",
        )

    elif etype == "TaxCollected":
        rev = p.get("total_tax_revenue", 0.0)
        badge = "[dim yellow]💰 TAX REVENUE[/]"
        return (
            badge,
            f"Day {tick:03d} | City Hall collected {rev:,.1f} C in daily municipal taxes.",
        )

    # Generic fallback
    return "[dim]ℹ️ EVENT[/]", f"Day {tick:03d} | {etype}"


def build_events_panel(events: list[Event], max_display: int = 8) -> Panel:
    """Format scrolling feed of major decisions, social crises, and municipal updates."""
    # Priority event types to feature in the main decision feed
    priority_types = {
        "StrategicDecisionMade",
        "RiotStarted",
        "RiotQuelled",
        "ElectionHeld",
        "MayoralTransition",
        "CorruptionScandalExposed",
        "PolicyEnacted",
        "PolicyExpired",
        "TimelineForked",
        "NewsPublished",
        "RumorSpawned",
        "AgentDied",
    }

    filtered = [e for e in events if e.event_type in priority_types]
    # If filtered is small, include other events
    if len(filtered) < max_display:
        filtered = events

    display_events = filtered[-max_display:]

    table = Table(box=None, expand=True, show_header=False, padding=(0, 1))
    table.add_column("Type", width=22)
    table.add_column("Details", ratio=1)

    if not display_events:
        table.add_row(
            "[dim]--[/]", "[dim]Awaiting daily events and major decisions...[/]"
        )
    else:
        for evt in display_events:
            badge, text = format_event_badge_and_text(evt)
            table.add_row(badge, text)

    return Panel(
        table,
        title="[bold magenta]⚡ Live Major Decisions, Civil Crises & Societal Event Feed[/]",
        border_style="magenta",
        padding=(0, 1),
    )


def build_controls_panel(run_id: str, tick: int) -> Panel:
    """Format on-screen operator hotkeys and intervention instructions."""
    grid = Table.grid(expand=True)
    grid.add_column(justify="left", ratio=1)
    grid.add_column(justify="right", ratio=1)

    left = Text()
    left.append("⏸️  [Ctrl+C] ", style="bold yellow")
    left.append("Pause Simulation  │  ", style="bold white")
    left.append("🔍 Inspect: ", style="dim")
    left.append(f"python cli.py inspect run {run_id}", style="cyan")

    right = Text()
    right.append("🌿 Take Action (Branch): ", style="dim")
    right.append(
        f"python cli.py branch {run_id} --tick {tick} --subsidy 0.30",
        style="bold green",
    )

    grid.add_row(left, right)
    return Panel(
        grid,
        style="dim blue",
        padding=(0, 1),
    )


def render_dashboard(
    state: WorldState,
    recent_events: list[Event],
    run_id: str,
    total_days: int,
    speed_name: str,
    max_feed_events: int = 8,
) -> Layout:
    """
    Assemble complete composite terminal UI layout with:
    - Top: Header banner with LLM Indicator Badge
    - Middle: 3-column telemetry (Macro/Finance, Demographics/Harmony, Politics/Stability)
    - Lower Middle: High-visibility scrolling major decision and event feed
    - Bottom: Operator controls bar with Pause & Intervene instructions
    """
    layout = Layout()

    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="telemetry", size=15),
        Layout(name="feed", size=8),
        Layout(name="controls", size=3),
    )

    # 1. Header
    header_panel = build_header_panel(
        run_id=run_id,
        tick=state.clock.current_tick,
        total_days=total_days,
        date_str=state.clock.format_date(),
        speed_name=speed_name,
        llm_enabled=getattr(state.llm_gateway, "enabled", False),
        llm_model=getattr(state.llm_gateway, "model_name", "qwen2.5:1.5b"),
    )
    layout["header"].update(header_panel)

    # 2. Middle 3-Column Telemetry
    layout["telemetry"].split_row(
        Layout(name="macro", ratio=4),
        Layout(name="demographics", ratio=4),
        Layout(name="politics", ratio=4),
    )

    layout["macro"].update(build_macro_panel(state))
    layout["demographics"].update(build_demographics_panel(state))
    layout["politics"].update(build_politics_panel(state))

    # 3. Scrolling Decision Feed
    layout["feed"].update(
        build_events_panel(recent_events, max_display=max_feed_events)
    )

    # 4. Operator Controls Footer Bar
    layout["controls"].update(
        build_controls_panel(run_id=run_id, tick=state.clock.current_tick)
    )

    return layout
