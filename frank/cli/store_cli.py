"""CLI commands for CalcStore and MolQueue."""

from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.table import Table

console = Console()


def _require_store():
    from ..store.database import init_db, is_store_available
    from ..store.repository import JobRepository
    try:
        repo = JobRepository()
        repo.ensure_tables()
        if not is_store_available():
            console.print("Error: database unavailable. Start PostgreSQL or use SQLite default.", style="red")
            console.print("  docker compose up -d", style="dim")
            sys.exit(1)
    except Exception as e:
        console.print(f"Error: store unavailable: {e}", style="red")
        sys.exit(1)


@click.group()
def store():
    """CalcStore — job history, search, and export."""
    pass


@store.command("init")
def store_init():
    """Initialize database tables."""
    from ..store.database import init_db
    init_db()
    console.print("[OK] Database tables created.", style="green")


@store.command("history")
@click.option("--limit", "-n", default=20, help="Max entries")
@click.option("--molecule", "-m", default=None, help="Filter by molecule")
@click.option("--method", default=None, help="Filter by method")
@click.option("--status", "-s", default=None, help="Filter by status")
def store_history(limit, molecule, method, status):
    """List recent calculation jobs."""
    _require_store()
    from ..store.repository import JobRepository
    jobs = JobRepository().list_jobs(limit=limit, molecule=molecule, method=method, status=status)
    if not jobs:
        console.print("No jobs found.", style="yellow")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Status")
    table.add_column("Molecule", style="cyan")
    table.add_column("Method")
    table.add_column("Basis")
    table.add_column("Energy (Ha)", justify="right")
    table.add_column("Duration (s)", justify="right")

    for j in jobs:
        short_id = j.id[:8]
        energy = f"{j.energy_hartree:.6f}" if j.energy_hartree is not None else "-"
        duration = f"{j.duration_sec:.1f}" if j.duration_sec is not None else "-"
        status_style = "green" if j.status == "completed" else "red" if j.status == "failed" else "yellow"
        table.add_row(
            short_id,
            f"[{status_style}]{j.status}[/{status_style}]",
            j.molecule_name or "-",
            j.method or "-",
            j.basis or "-",
            energy,
            duration,
        )
    console.print(table)
    console.print(f"\n{len(jobs)} job(s). Use 'frank show <id>' for details.", style="dim")


@store.command("show")
@click.argument("job_id")
def store_show(job_id):
    """Show details for a job (full or partial UUID)."""
    _require_store()
    from ..store.repository import JobRepository
    from ..queue.service import get_job_status

    repo = JobRepository()
    resolved = _resolve_job_id(repo, job_id)
    if not resolved:
        console.print(f"Job not found: {job_id}", style="red")
        return

    info = get_job_status(resolved)
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    for key, val in info.items():
        table.add_row(key, str(val) if val is not None else "-")
    console.print(table)


@store.command("compare")
@click.argument("job_id_a")
@click.argument("job_id_b")
def store_compare(job_id_a, job_id_b):
    """Compare two calculation jobs."""
    _require_store()
    from ..store.repository import JobRepository
    repo = JobRepository()
    a = _resolve_job_id(repo, job_id_a)
    b = _resolve_job_id(repo, job_id_b)
    if not a or not b:
        console.print("One or both jobs not found.", style="red")
        return
    try:
        result = repo.compare_jobs(a, b)
    except KeyError:
        console.print("One or both jobs not found.", style="red")
        return

    console.print("\nJob comparison:", style="bold")
    for label, data in [("A", result["job_a"]), ("B", result["job_b"])]:
        console.print(f"\n  Job {label} ({data['id'][:8]})", style="cyan")
        for k, v in data.items():
            if k != "id":
                console.print(f"    {k}: {v}")

    if result["delta"]:
        console.print("\n  Delta (B − A):", style="bold")
        for k, v in result["delta"].items():
            console.print(f"    {k}: {v:.6f}" if isinstance(v, float) else f"    {k}: {v}")


@store.command("export")
@click.option("--format", "fmt", type=click.Choice(["csv", "json"]), default="csv")
@click.option("--output", "-o", default=None, help="Output file (stdout if omitted)")
@click.option("--molecule", "-m", default=None)
@click.option("--method", default=None)
@click.option("--limit", "-n", default=1000)
def store_export(fmt, output, molecule, method, limit):
    """Export stored jobs to CSV or JSON."""
    _require_store()
    from ..store.repository import JobRepository
    repo = JobRepository()
    if fmt == "csv":
        content = repo.export_csv(molecule=molecule, method=method, limit=limit)
    else:
        content = repo.export_json(molecule=molecule, method=method, limit=limit)

    if output:
        with open(output, "w",encoding="utf-8") as f:
            f.write(content)
        console.print(f"[OK] Exported to {output}", style="green")
    else:
        console.print(content)


def _resolve_job_id(repo, partial_id: str) -> str | None:
    """Resolve partial UUID prefix to full job id."""
    if len(partial_id) >= 36:
        job = repo.get_job(partial_id)
        return job["id"] if job else None
    jobs = repo.list_jobs(limit=500)
    matches = [j for j in jobs if j.id.startswith(partial_id)]
    if len(matches) == 1:
        return matches[0].id
    if len(matches) > 1:
        console.print("Ambiguous job id prefix; be more specific.", style="yellow")
        return None
    return None


@click.command()
@click.argument("query", nargs=-1, type=str)
@click.option("--timeout", "-t", default=600, help="Timeout in seconds")
def submit(query, timeout):
    """Submit an async calculation job to MolQueue."""
    if not query:
        console.print("Please provide a calculation request.", style="red")
        return
    _require_store()
    text = " ".join(query)
    from ..agent import FrankAgent
    from ..queue.service import JobSubmissionService

    service = JobSubmissionService(agent=FrankAgent(timeout=timeout), timeout=timeout)
    try:
        result = service.submit(text)
    except Exception as e:
        console.print(f"Error submitting job: {e}", style="red")
        console.print("Ensure Redis is running: docker compose up -d", style="dim")
        return

    if result.is_workflow:
        console.print(f"\n[OK] {result.message}", style="green")
        console.print(f"  Workflow ID: {result.workflow_id}", style="dim")
        console.print(f"  Celery chain: {result.celery_id}", style="dim")
        console.print(f"  Check status: frank workflow-status {result.workflow_id[:8]}", style="dim")
    elif result.job_id:
        console.print(f"\n[OK] {result.message}", style="green")
        console.print(f"  Job ID: {result.job_id}", style="dim")
        console.print(f"  Celery task: {result.celery_id}", style="dim")
        console.print(f"  Check status: frank status {result.job_id[:8]}", style="dim")
    else:
        console.print(result.message or "Submission failed.", style="red")


@click.command()
@click.argument("job_id")
def status(job_id):
    """Check status of an async job."""
    _require_store()
    from ..store.repository import JobRepository
    from ..queue.service import get_job_status

    repo = JobRepository()
    resolved = _resolve_job_id(repo, job_id)
    if not resolved:
        console.print(f"Job not found: {job_id}", style="red")
        return

    info = get_job_status(resolved)
    st = info["status"]
    color = "green" if st == "completed" else "red" if st == "failed" else "yellow"
    console.print(f"Job {info['id'][:8]}... [{color}]{st}[/{color}]")
    if info.get("molecule"):
        console.print(f"  Molecule: {info['molecule']}")
    if info.get("method"):
        console.print(f"  Method: {info['method']} / {info.get('basis', '-')}")
    if info.get("duration_sec"):
        console.print(f"  Duration: {info['duration_sec']:.1f} s")
    if info.get("energy_hartree") is not None:
        console.print(f"  Energy: {info['energy_hartree']:.8f} Ha")
    if info.get("error_message"):
        console.print(f"  Error: {info['error_message']}", style="red")
    if info.get("run_dir"):
        console.print(f"  Run dir: {info['run_dir']}", style="dim")


@click.command("workflow-status")
@click.argument("workflow_id")
def workflow_status(workflow_id):
    """Check status of an async workflow."""
    _require_store()
    from ..store.repository import JobRepository
    from ..queue.service import get_workflow_status

    repo = JobRepository()
    wf = _resolve_workflow_id(repo, workflow_id)
    if not wf:
        console.print(f"Workflow not found: {workflow_id}", style="red")
        return

    info = get_workflow_status(wf)
    color = "green" if info["status"] == "completed" else "red" if info["status"] == "failed" else "yellow"
    console.print(f"\n{info['title']} [{color}]{info['status']}[/{color}]", style="bold")
    console.print(f"  Type: {info['workflow_type']}", style="dim")

    table = Table(show_header=True, box=None)
    table.add_column("#", style="dim")
    table.add_column("Molecule", style="cyan")
    table.add_column("Status")
    table.add_column("Energy (Ha)", justify="right")
    for step in info["steps"]:
        sc = "green" if step["status"] == "completed" else "red" if step["status"] == "failed" else "yellow"
        energy = f"{step['energy_hartree']:.6f}" if step.get("energy_hartree") is not None else "-"
        table.add_row(str(step["step"]), step.get("molecule") or "-", f"[{sc}]{step['status']}[/{sc}]", energy)
    console.print(table)


def _resolve_workflow_id(repo, partial_id: str) -> str | None:
    wf = repo.get_workflow(partial_id)
    if wf:
        return wf["id"]
    from ..store.models import WorkflowRecord
    from ..store.database import get_session
    from sqlalchemy import select
    with get_session() as session:
        rows = session.scalars(select(WorkflowRecord)).all()
        matches = [w for w in rows if w.id.startswith(partial_id)]
        if len(matches) == 1:
            return matches[0].id
    return None


def register_store_commands(main_group):
    """Register store/queue commands on the main CLI group."""
    main_group.add_command(store)
    main_group.add_command(submit)
    main_group.add_command(status)
    main_group.add_command(workflow_status)

    # Convenience aliases
    main_group.add_command(store_history := store.commands["history"], name="history")
    main_group.add_command(store_show := store.commands["show"], name="show")
