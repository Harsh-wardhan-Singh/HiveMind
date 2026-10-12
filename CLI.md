# HIVEMIND — Operator CLI Guide & Quickstart

Welcome to **HIVEMIND**, an agent-based macroeconomic, civic governance, and information ecology simulation platform.

---

## ⚡ 30-Second Quickstart & Cheat Sheet

The core operator loop consists of 4 simple steps: **Run ➔ Pause ➔ Inspect ➔ Intervene**.

```text
 ┌──────────────┐      Ctrl+C      ┌───────────────┐
 │  1. RUN      │ ───────────────> │  2. PAUSE     │
 │  Simulation  │                  │  Snapshot Saved
 └──────────────┘                  └───────┬───────┘
        ▲                                  │
        │ python cli.py compare            ▼
 ┌──────┴───────┐   python cli.py  ┌───────────────┐
 │  4. BRANCH   │ <─────────────── │  3. INSPECT   │
 │  & Intervene │      branch      │  City & Mayor │
 └──────────────┘                  └───────────────┘
```

### Essential Commands (Copy & Paste)

| Action | Command | What It Does |
| :--- | :--- | :--- |
| **Run (Standard)** | `python cli.py run --days 365 --speed normal` | Launches the live terminal dashboard. |
| **Run with LLM** | `python cli.py run --days 365 --llm` | Enables Ollama AI reasoning (`qwen2.5:1.5b`). |
| **Turn-by-Turn Mode** | `python cli.py run --days 30 --step` | Advances one day at a time on [Enter]. |
| **Pause Simulation** | Press `Ctrl+C` anytime | Safely stops, captures snapshot, and prints action menu. |
| **Inspect City State** | `python cli.py inspect run <run_id>` | Shows GDP, CPI, unrest, treasury, and mayor. |
| **Inspect Decisions** | `python cli.py inspect events <run_id> --limit 15` | Shows recent LLM decrees, riots, elections, scandals. |
| **Inspect Citizen** | `python cli.py inspect agent agent_001` | Shows OCEAN traits, rumors, cash, job, and unrest. |
| **Take Action / Fork** | `python cli.py branch <run_id> --tick 45 --subsidy 0.30` | Enacts policy and creates a new timeline branch. |
| **Compare Timelines** | `python cli.py compare <baseline_id> <branch_id>` | Side-by-side delta matrix of policy impacts. |
| **Export Telemetry** | `python cli.py export <run_id> --format json` | Exports full dataset to JSON or CSV. |

---

## 🎮 How to Pause & Take Action (Operator Playbook)

### 1. How to Pause at Any Time
While the simulation is running, **press `Ctrl+C`**.
* The simulation immediately halts safely without corrupting the database.
* An authoritative point-in-time snapshot (`snap_<run_id>_<tick>`) is saved.
* An **Operator Intervention & Action Menu** prints directly to your terminal showing your Run ID, Day, and copy-pasteable commands.

---

### 2. How to Inspect What Happened
Before taking action, check what caused the distress in your city:
```bash
# View full city macroeconomic and political health:
python cli.py inspect run <run_id>

# View the most recent major decisions, riots, and scandals:
python cli.py inspect events <run_id> --limit 15

# View district unrest or rioting status:
python cli.py inspect district dist_industrial
```

---

### 3. How to Intervene & Enact Policies (`branch`)
Use `python cli.py branch` to fork the timeline from the paused day and apply emergency policies:

#### Scenario A: High Unrest & Rioting?
Enact a **Food Subsidy** (+30%) to reduce cost-of-living and appease citizens:
```bash
python cli.py branch <run_id> --tick <paused_day> --subsidy 0.30 --days 60
```

#### Scenario B: Soaring Inflation (CPI)?
Enact **Fiscal Austerity** (+20%) and raise **Corporate Taxes** (25%) to cool demand:
```bash
python cli.py branch <run_id> --tick <paused_day> --austerity 0.20 --corp-tax 0.25 --days 60
```

#### Scenario C: Municipal Treasury Depletion?
Inject an emergency **Treasury Grant** (+25,000 Credits) to keep public services funded:
```bash
python cli.py branch <run_id> --tick <paused_day> --grant 25000 --days 60
```

#### Scenario D: High Unemployment?
Launch a **Public Works Project** paying civic wages:
```bash
python cli.py branch <run_id> --tick <paused_day> --public-works 40.0 --days 60
```

---

### 4. How to Resume Without Changing Policies
If you just wanted to pause to inspect the numbers and now want to continue running:
```bash
python cli.py branch <run_id> --tick <paused_day> --name "Resumed Run" --days 300
```

---

### 5. How to Compare Policy Results
Measure whether your intervention succeeded by comparing the original timeline against your branch:
```bash
python cli.py compare <original_run_id> <branch_run_id>
```
Output:
```text
      Differential Trajectory Comparison: Branch A (Subsidy) vs Baseline
┌──────────────────────┬────────────────┬────────────────┬─────────────────┬──────────┐
│ Societal Metric      │   Baseline (B) │     Branch (A) │  Terminal Delta │      Δ % │
├──────────────────────┼────────────────┼────────────────┼─────────────────┼──────────┤
│ treasury_balance     │       92,279.8 │       75,410.2 │       -16,869.6 │   -18.3% │
│ cpi                  │          94.47 │          82.10 │          -12.37 │   -13.1% │
│ approval_rating      │          64.0% │          91.5% │          +27.5% │   +43.0% │
│ city_unrest          │           0.42 │           0.14 │           -0.28 │   -66.7% │
│ society_harmony_index│          61.0% │          84.2% │          +23.2% │   +38.0% │
└──────────────────────┴────────────────┴────────────────┴─────────────────┴──────────┘
```

---

## 🖥️ Understanding the Live Dashboard

When running `python cli.py run`, the terminal renders a 4-section layout:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🏛️ HIVEMIND [run_8f1a2b]    Day 045 / 365 (12%)  •  Year 1, Day 46           │
│                                           ● LLM REASONING: qwen2.5:1.5b     │
├─────────────────────────┬─────────────────────────┬─────────────────────────┤
│ 📊 Macroeconomics       │ 👥 Demographics         │ ⚖️ Municipal Governance │
│   • GDP: 9,821 C        │   • Pop: 100 alive      │   • Mayor: agent_001    │
│   • CPI: 94.47          │   • Health: 93.0%       │   • Approval: 100.0%    │
│   • Inflation: -5.5%    │   • Harmony: 80.1%      │   • Favorability: 0.60  │
│   • Treasury: 94,857 C  │   • Distrust: 19.9%     │   • Unrest: 0.13        │
│   • Solvency: 9/9 corps │   • LLM Decisions: 2    │   • Active Riots: 0     │
├─────────────────────────┴─────────────────────────┴─────────────────────────┤
│ ⚡ Live Major Decisions, Civil Crises & Societal Event Feed                 │
│   ⚡ LLM DECISION   Day 045 | MAYOR enacted 'FOOD_SUBSIDY' -> Low income... │
│   💰 TAX REVENUE    Day 045 | City Hall collected 1,288 C in municipal taxes│
│   📰 NEWS BROADCAST Day 044 | [Civic Chronicle] Food relief stabilizes CPI  │
├─────────────────────────────────────────────────────────────────────────────┤
│ ⏸️ [Ctrl+C] Pause & Intervene │ 🔍 Inspect: python cli.py inspect run ...   │
│                               │ 🌿 Branch:  python cli.py branch ...        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### LLM Status Badge
- `● LLM REASONING: qwen2.5:1.5b` (green): 3–5% of strategic decisions are evaluated by your local Ollama LLM.
- `○ 100% MATH FALLBACK` (yellow): Offline mathematical utility equations govern decisions autonomously. No Ollama required!

### Event Badges in Feed
- `⚡ LLM DECISION`: Mayoral emergency decree or corporate CEO strategy made by local LLM.
- `⚙️ MATH FALLBACK`: Strategic decision made by deterministic utility math.
- `🔥 RIOT STARTED`: Civil unrest exceeded threshold; district riots started.
- `🛡️ RIOT QUELLED`: Public safety intervention restored civic peace.
- `🗳️ ELECTION HELD`: Municipal democratic balloting concluded.
- `👑 MAYORAL TRANSFER`: Inauguration of newly elected city mayor.
- `⚠️ SCANDAL EXPOSED`: Investigative leak uncovered City Hall corruption.
- `📜 POLICY ENACTED`: Fiscal or relief policy decree took effect.

---

## 📖 Command Reference

### `python cli.py run`
Runs the simulation engine.
```bash
python cli.py run [OPTIONS]
```
* `--days`, `-d INTEGER`: Duration in days [default: 365].
* `--speed TEXT`: Execution speed: `slow` (0.3s/tick), `normal` (0.08s/tick), `fast` (0.01s/tick), `max` (0s/tick) [default: normal].
* `--step`: Turn-by-turn mode (press [Enter] each day, 'q' to pause and intervene).
* `--llm / --no-llm`: Enable local Ollama LLM reasoning [default: False].
* `--headless`: Disable terminal UI (for scripts or background benchmarks).
* `--population`, `-p INTEGER`: Starting citizen population [default: 100].
* `--seed`, `-s INTEGER`: PRNG seed [default: 424242].

### `python cli.py inspect`
Inspects authoritative entities and events:
* `python cli.py inspect run <run_id>`: Overall run summary.
* `python cli.py inspect events <run_id> [--type <TYPE>] [--limit <N>]`: Filtered event stream.
* `python cli.py inspect agent <agent_id>`: Citizen profile, OCEAN traits, rumors.
* `python cli.py inspect company <company_id>`: Corporate balance sheet and inventory.
* `python cli.py inspect district <district_id>`: District rent, unrest, and safety.

### `python cli.py branch`
Forks the timeline with policy overrides:
* `--tick`, `-t INTEGER`: Day to fork from (**required**).
* `--subsidy FLOAT`: Food subsidy magnitude [0.0 - 0.50].
* `--austerity FLOAT`: Austerity spending reduction [0.0 - 1.0].
* `--stimulus FLOAT`: Welfare grant per citizen.
* `--public-works FLOAT`: Public works daily wage.
* `--corp-tax FLOAT`: Corporate profit tax rate [0.0 - 1.0].
* `--grant FLOAT`: Cash injected into municipal treasury.
* `--days`, `-d INTEGER`: Advance forward immediately after branching.

### `python cli.py compare`
Compares two runs:
```bash
python cli.py compare <baseline_run_id> <branch_run_id>
```

### `python cli.py export`
Exports telemetry:
```bash
python cli.py export <run_id> --format json --output run_telemetry.json
python cli.py export <run_id> --format csv  --output run_telemetry.csv
```

---

*HIVEMIND — Built for macroeconomic modeling, civic governance research, and counterfactual scenario exploration.*
