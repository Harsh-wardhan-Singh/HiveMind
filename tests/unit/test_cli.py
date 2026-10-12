"""Unit tests for Phase 9 Operator Administrative CLI."""

import os
import tempfile

from typer.testing import CliRunner

from backend.cli.main import app

runner = CliRunner()


def test_cli_version():
    """Verify version command outputs correct Phase 9 version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "HIVEMIND" in result.stdout
    assert "1.0.0" in result.stdout


def test_cli_help():
    """Verify top-level help menu lists all primary commands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout
    assert "inspect" in result.stdout
    assert "branch" in result.stdout
    assert "replay" in result.stdout
    assert "compare" in result.stdout
    assert "export" in result.stdout


def test_cli_run_headless_and_inspect():
    """Verify headless simulation run and subsequent entity inspections."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = os.path.join(tmpdir, "test_sim.db")
        db_url = f"sqlite:///{db_path}"

        # 1. Run headless simulation for 3 days
        run_res = runner.invoke(
            app,
            [
                "run",
                "--days",
                "3",
                "--population",
                "15",
                "--headless",
                "--run-id",
                "sim_cli_test",
                "--database-url",
                db_url,
            ],
        )
        assert run_res.exit_code == 0
        assert "SIMULATION RUN COMPLETE" in run_res.stdout
        assert "sim_cli_test" in run_res.stdout

        # 2. Inspect Run
        insp_run = runner.invoke(
            app, ["inspect", "run", "sim_cli_test", "--db", db_url]
        )
        assert insp_run.exit_code == 0
        assert "Simulation Run Diagnostics" in insp_run.stdout
        assert "Target Duration" in insp_run.stdout

        # 3. Inspect Agent
        insp_agent = runner.invoke(
            app,
            [
                "inspect",
                "agent",
                "agent_0001",
                "--run-id",
                "sim_cli_test",
                "--db",
                db_url,
            ],
        )
        assert insp_agent.exit_code == 0
        assert "Citizen Profile" in insp_agent.stdout
        assert "agent_0001" in insp_agent.stdout

        # 4. Inspect Company
        insp_comp = runner.invoke(
            app,
            [
                "inspect",
                "company",
                "comp_food_01",
                "--run-id",
                "sim_cli_test",
                "--db",
                db_url,
            ],
        )
        assert insp_comp.exit_code == 0
        assert "Corporate Enterprise" in insp_comp.stdout
        assert "comp_food_01" in insp_comp.stdout

        # 5. Inspect District
        insp_dist = runner.invoke(
            app,
            [
                "inspect",
                "district",
                "dist_central",
                "--run-id",
                "sim_cli_test",
                "--db",
                db_url,
            ],
        )
        assert insp_dist.exit_code == 0
        assert "Municipal District" in insp_dist.stdout
        assert "dist_central" in insp_dist.stdout

        # 6. Inspect Events
        insp_evts = runner.invoke(
            app, ["inspect", "events", "sim_cli_test", "--limit", "10", "--db", db_url]
        )
        assert insp_evts.exit_code == 0
        assert "Event Stream" in insp_evts.stdout


def test_cli_branch_compare_replay_export():
    """Verify branch fork, trajectory comparison, time-travel replay, and data export."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = os.path.join(tmpdir, "test_branch.db")
        db_url = f"sqlite:///{db_path}"

        # 1. Base run to Day 4
        runner.invoke(
            app,
            [
                "run",
                "--days",
                "4",
                "--population",
                "20",
                "--headless",
                "--run-id",
                "run_parent",
                "--database-url",
                db_url,
            ],
        )

        # 2. Branch at Day 2
        branch_res = runner.invoke(
            app,
            [
                "branch",
                "run_parent",
                "--tick",
                "2",
                "--name",
                "Branch Subsidy",
                "--branch-id",
                "run_branch_sub",
                "--subsidy",
                "0.30",
                "--days",
                "2",
                "--database-url",
                db_url,
            ],
        )
        assert branch_res.exit_code == 0
        assert "Counterfactual Branch Summary" in branch_res.stdout
        assert "run_branch_sub" in branch_res.stdout

        # 3. Compare Parent vs Branch
        comp_res = runner.invoke(
            app,
            [
                "compare",
                "run_parent",
                "run_branch_sub",
                "--database-url",
                db_url,
            ],
        )
        assert comp_res.exit_code == 0
        assert "Differential Trajectory Comparison" in comp_res.stdout
        assert "treasury" in comp_res.stdout.lower()

        # 4. Replay Parent at Day 4
        replay_res = runner.invoke(
            app,
            [
                "replay",
                "run_parent",
                "--tick",
                "4",
                "--database-url",
                db_url,
            ],
        )
        assert replay_res.exit_code == 0
        assert "Time-Travel Event Replay Summary" in replay_res.stdout
        assert "100% Bit-for-Bit Determinism Parity Verified" in replay_res.stdout

        # 5. Export Parent to JSON & CSV
        json_file = os.path.join(tmpdir, "export.json")
        csv_file = os.path.join(tmpdir, "export.csv")

        exp_json = runner.invoke(
            app,
            [
                "export",
                "run_parent",
                "--format",
                "json",
                "--output",
                json_file,
                "--database-url",
                db_url,
            ],
        )
        assert exp_json.exit_code == 0
        assert os.path.exists(json_file)

        exp_csv = runner.invoke(
            app,
            [
                "export",
                "run_parent",
                "--format",
                "csv",
                "--output",
                csv_file,
                "--database-url",
                db_url,
            ],
        )
        assert exp_csv.exit_code == 0
        assert os.path.exists(csv_file)
