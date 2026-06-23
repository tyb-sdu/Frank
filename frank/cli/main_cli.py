import os
import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from rich.text import Text

from .. import __version__
from ..agent import FrankAgent
from .agent_factory import create_agent
from ..molecules.database import list_molecules, get_molecule, search_molecules, get_xyz_block, list_tags
from ..basis import list_basis_sets
from ..methods.dft import list_dft_functionals, list_dft_categories
from ..methods.post_hf import list_post_hf_methods
from ..methods.excited import list_excited_methods
from ..methods.relativistic import list_relativistic_methods
from ..methods.casscf import list_multiref_methods
from ..methods.solvation import list_solvents, list_solvation_models
from ..core.diagnostics import format_diagnostics
from ..core.visualizer import plot_result, plot_method_comparison, plot_basis_convergence, HAS_PLT


console = Console()


def print_banner():
    """Print a clean, academic-style banner."""
    banner = f"Frank -- Computational Chemistry Terminal Agent v{__version__}"
    console.print(banner, style="bold cyan")
    console.print("Code generation, execution, diagnostics, and interpretation", style="dim")


def print_code_result(result: dict):
    """Display parsed intent and generated code."""
    if result.get("is_chat"):
        console.print(f"\n{result['chat_message']}\n")
        return

    intent = result["intent"]
    code = result["code"]
    warnings = result["warnings"]

    if warnings:
        for w in warnings:
            console.print(f"Warning: {w}", style="yellow")

    if not code:
        console.print("Error: unable to generate code; please verify input.", style="red")
        return

    console.print("\nParsed intent:", style="bold")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Parameter", style="cyan")
    table.add_column("Value")

    if intent.molecule:
        try:
            mol = get_molecule(intent.molecule)
            table.add_row("Molecule", f"{mol.name_cn} ({mol.formula})")
        except:
            table.add_row("Molecule", intent.molecule)

    if intent.method:
        table.add_row("Method", intent.method)
    if intent.basis:
        table.add_row("Basis set", intent.basis)
    if intent.calc_type:
        type_names = {
            "energy": "Single-point energy",
            "geometry": "Geometry optimization",
            "frequency": "Frequency analysis",
            "excited": "Excited state",
            "casscf": "CASSCF",
            "nbo": "NBO analysis",
        }
        table.add_row("Calculation type", type_names.get(intent.calc_type, intent.calc_type))
    if intent.solvent:
        table.add_row("Solvent", intent.solvent)
    if intent.n_states:
        table.add_row("Excited states", str(intent.n_states))
    if intent.norb and intent.nelec:
        table.add_row("Active space", f"({intent.norb}, {intent.nelec})")

    console.print(table)

    conf = intent.confidence
    conf_color = "green" if conf > 0.7 else "yellow" if conf > 0.4 else "red"
    console.print(f"\nConfidence: {conf:.0%}", style=conf_color)

    # Code walkthrough
    if code.blocks:
        console.print("\nCode summary:", style="bold")
        walkthrough = Table(show_header=True, box=None, padding=(0, 2))
        walkthrough.add_column("Section", style="cyan")
        walkthrough.add_column("Description")
        for block in sorted(code.blocks, key=lambda b: b.order):
            if block.description:
                walkthrough.add_row(block.section.replace("_", " ").title(), block.description)
        console.print(walkthrough)

    console.print("\nGenerated code:", style="bold")
    script = code.to_script()
    syntax = Syntax(script, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=code.title, border_style="green"))

    if code.run_instructions:
        console.print(f"\nUsage: {code.run_instructions}", style="bold")


def print_execution_result(result: dict, show_plot: bool = True):
    """Display execution results with diagnostics and interpretation."""
    execution = result.get("execution")
    parsed = result.get("parsed", {})
    diagnostics = result.get("diagnostics", [])
    interpretation = result.get("interpretation", "")

    if not execution:
        console.print("Error: calculation was not executed.", style="red")
        return

    retry_log = result.get("retry_log", [])
    if retry_log:
        console.print("\nAutomatic recovery log:", style="bold yellow")
        for entry in retry_log:
            console.print(f"   {entry}")

    if execution.success:
        console.print(f"\n[OK] Calculation succeeded (duration {execution.duration:.1f} s)", style="green")
        if execution.output_dir:
            console.print(f"   Run directory: {execution.output_dir}", style="dim")
    else:
        console.print(f"\n[FAIL] Calculation failed", style="red")
        if execution.error_type:
            console.print(f"   Error type: {execution.error_type}")
        if execution.error_message:
            console.print(f"   Error message: {execution.error_message}")
        # Show plain-language explanation if available
        plain = result.get("plain_language", "")
        if plain:
            console.print(f"\n   Explanation: {plain}", style="yellow")
        error_diag = result.get("error_diagnosis", "")
        if error_diag:
            console.print(error_diag, style="yellow")

    if diagnostics:
        console.print("\nDiagnostics:", style="bold")
        console.print(format_diagnostics(diagnostics))

    if interpretation:
        console.print(interpretation)

    if show_plot and parsed and HAS_PLT:
        try:
            plot_result(parsed)
            freq = parsed.get("frequency")
            intent = result.get("intent")
            if freq and intent and intent.molecule:
                from ..core.spectrum_reference import (
                    get_reference_spectrum, compare_with_reference, format_comparison_report,
                )
                ref = get_reference_spectrum(intent.molecule)
                if ref and freq.frequencies:
                    comparison = compare_with_reference(freq.frequencies, ref)
                    console.print("\nIR 实验对照:", style="bold")
                    console.print(format_comparison_report(comparison))
        except Exception as e:
            console.print(f"Warning: plot generation failed: {e}", style="dim")

    if execution.stdout:
        console.print("\nStandard output (last 20 lines):", style="dim")
        lines = execution.stdout.strip().split("\n")
        for line in lines[-20:]:
            console.print(f"  {line}", style="dim")


@click.group(invoke_without_command=True)
@click.option("--classic", is_flag=True, help="Use classic FrankAgent instead of LangGraph")
@click.pass_context
def main(ctx, classic):
    ctx.ensure_object(dict)
    ctx.obj["classic"] = classic
    if ctx.invoked_subcommand is None:
        interactive_mode(classic=classic)


@main.command()
@click.argument("query", nargs=-1, type=str)
@click.pass_context
def ask(ctx, query):
    """Generate code only (no execution)."""
    if not query:
        console.print("Please provide a calculation request.", style="red")
        return

    text = " ".join(query)
    agent = create_agent(classic=ctx.obj.get("classic", False))
    result = agent.process_request(text)
    print_code_result(result)


@main.command()
@click.argument("query", nargs=-1, type=str)
@click.option("--no-interpret", is_flag=True, help="Skip result interpretation")
@click.option("--no-plot", is_flag=True, help="Skip plots")
@click.option("--timeout", "-t", default=600, help="Timeout in seconds")
@click.option("--export", "-e", default=None, help="Export results to file")
@click.option("--export-format", default="json", type=click.Choice(["json", "csv"]), help="Export format")
@click.pass_context
def run(ctx, query, no_interpret, no_plot, timeout, export, export_format):
    """Generate code and execute the calculation."""
    if not query:
        console.print("Please provide a calculation request.", style="red")
        return

    text = " ".join(query)
    console.print(f"\nExecuting calculation...", style="bold")

    agent = create_agent(timeout=timeout, classic=ctx.obj.get("classic", False))
    result = agent.run(text, interpret=not no_interpret)

    if result["code"]:
        console.print("\nGenerated code:", style="bold")
        script = result["script"]
        syntax = Syntax(script[:2000] + "\n..." if len(script) > 2000 else script,
                       "python", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=result["code"].title, border_style="green"))

    show_plot = not no_plot
    print_execution_result(result, show_plot=show_plot)

    # Export results if requested
    if export and result.get("execution"):
        from ..workflows.export import export_to_json, export_to_csv
        if export_format == "csv":
            export_to_csv(result, export)
            console.print(f"\nResults exported to {export} (CSV)", style="dim")
        else:
            export_to_json(result, export)
            console.print(f"\nResults exported to {export} (JSON)", style="dim")


def print_workflow_plan(plan):
    """Display a planned multi-step workflow."""
    console.print(f"\nWorkflow plan: {plan.title}", style="bold")
    console.print(f"  Type: {plan.workflow_type}")
    console.print(f"  Method: {plan.method} / {plan.basis}")
    console.print(f"  Description: {plan.description}")
    conf_color = "green" if plan.confidence > 0.7 else "yellow" if plan.confidence > 0.4 else "red"
    console.print(f"  Confidence: {plan.confidence:.0%}", style=conf_color)

    if plan.warnings:
        for w in plan.warnings:
            console.print(f"  Warning: {w}", style="yellow")

    if plan.tasks:
        console.print("\n  Steps:", style="bold")
        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("#", style="dim")
        table.add_column("Agent", style="cyan")
        table.add_column("Description")
        for i, task in enumerate(plan.tasks, 1):
            table.add_row(str(i), task.agent, task.description)
        console.print(table)


def print_autonomous_result(result: dict, agent=None):
    """Display autonomous orchestration results."""
    if result.get("awaiting_confirmation"):
        plan = result.get("plan")
        if plan:
            print_workflow_plan(plan)
        console.print(
            "\nWorkflow paused — awaiting confirmation before execution.",
            style="yellow",
        )
        if agent is not None and result.get("thread_id"):
            if Confirm.ask("Execute this workflow?", default=True):
                result = agent.resume(result["thread_id"], confirmed=True)
            else:
                console.print("Workflow cancelled.", style="dim")
                return
        else:
            console.print(
                f"Resume with thread_id={result.get('thread_id')} after confirmation.",
                style="dim",
            )
            return

    plan = result.get("plan")
    if plan:
        print_workflow_plan(plan)

    for w in result.get("warnings", []):
        console.print(f"Warning: {w}", style="yellow")

    orch = result.get("result")
    if orch and orch.summary:
        console.print(orch.summary)
    elif result.get("summary"):
        console.print(result["summary"])

    if result.get("success"):
        console.print("\n[OK] Autonomous workflow completed.", style="green")
    elif not result.get("fallback"):
        console.print("\n[FAIL] Autonomous workflow did not complete successfully.", style="red")


@main.command()
@click.argument("query", nargs=-1, type=str)
@click.pass_context
def plan(ctx, query):
    """Design a multi-step workflow without executing (Aitomia-style planner)."""
    if not query:
        console.print("Please provide a workflow description.", style="red")
        return
    text = " ".join(query)
    agent = create_agent(classic=ctx.obj.get("classic", False))
    wf_plan = agent.plan_workflow(text)
    print_workflow_plan(wf_plan)
    if not wf_plan.is_complex:
        console.print(
            "\nTip: This looks like a single-step calculation. Use 'frank ask' or 'frank run'.",
            style="dim",
        )
    else:
        console.print("\nTo execute: frank auto " + " ".join(query), style="dim")


@main.command("auto")
@click.argument("query", nargs=-1, type=str)
@click.option("--timeout", "-t", default=600, help="Timeout in seconds")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt for complex workflows")
@click.pass_context
def auto_run(ctx, query, timeout, yes):
    """Autonomously plan and execute a complex multi-step workflow."""
    if not query:
        console.print("Please provide a workflow description.", style="red")
        return
    text = " ".join(query)
    console.print("\nPlanning and executing autonomous workflow...", style="bold")
    agent = create_agent(timeout=timeout, classic=ctx.obj.get("classic", False))
    result = agent.run_autonomous(
        text,
        require_confirmation=not yes,
        confirmed=yes,
    )
    print_autonomous_result(result, agent=agent)


@main.command()
@click.argument("question", nargs=-1, type=str)
@click.pass_context
def explain(ctx, question):
    """Answer computational chemistry questions using the knowledge base (RAG-lite)."""
    if not question:
        console.print("Please provide a question.", style="red")
        return
    text = " ".join(question)
    agent = create_agent(classic=ctx.obj.get("classic", False))
    answer = agent.explain(text)
    console.print(Markdown(answer))


WORKFLOW_ALIASES = {
    "opt_freq": "opt_freq", "of": "opt_freq",
    "method_comparison": "method_comparison", "mc": "method_comparison", "compare": "method_comparison",
    "basis_convergence": "basis_convergence", "bc": "basis_convergence", "converge": "basis_convergence",
    "pes_scan": "pes_scan", "pes": "pes_scan",
    "solvation": "solvation", "solv": "solvation",
}

WORKFLOW_TYPES = list(WORKFLOW_ALIASES.keys())


@main.command()
@click.argument("workflow_type", type=click.Choice(WORKFLOW_TYPES))
@click.argument("molecule")
@click.option("--method", "-m", default="B3LYP", help="Computational method")
@click.option("--basis", "-b", default="6-31g*", help="Basis set")
@click.option("--methods", help="Method list (comma-separated)")
@click.option("--basis-sets", help="Basis set list (comma-separated)")
@click.option("--solvent", default="water", help="Solvent (for solvation workflow)")
@click.option("--scan-type", default="bond", help="Scan type (bond/angle/dihedral)")
@click.option("--atoms", default="0,1", help="Atom indices (comma-separated)")
@click.option("--n-points", default=11, type=int, help="Number of scan points")
@click.option("--range-start", default=0.8, type=float, help="Scan range start")
@click.option("--range-end", default=2.0, type=float, help="Scan range end")
@click.option("--timeout", "-t", default=600, help="Timeout in seconds")
@click.option("--export", "-e", default=None, help="Export results to file")
@click.option("--export-format", default="json", type=click.Choice(["json", "csv"]), help="Export format")
@click.pass_context
def workflow(ctx, workflow_type, molecule, method, basis, methods, basis_sets,
             solvent, scan_type, atoms, n_points, range_start, range_end, timeout,
             export, export_format):
    """Run multi-step computational workflows."""
    canonical_type = WORKFLOW_ALIASES.get(workflow_type, workflow_type)
    console.print(f"\nRunning workflow: {canonical_type}...", style="bold")

    agent = create_agent(timeout=timeout, classic=ctx.obj.get("classic", False))

    kwargs = {}
    if methods:
        kwargs["methods"] = [m.strip() for m in methods.split(",")]
    if basis_sets:
        kwargs["basis_sets"] = [b.strip() for b in basis_sets.split(",")]
    if solvent:
        kwargs["solvent"] = solvent
    if atoms:
        kwargs["atoms"] = atoms
    if scan_type:
        kwargs["scan_type"] = scan_type
    if n_points:
        kwargs["n_points"] = n_points
    if range_start:
        kwargs["range_start"] = range_start
    if range_end:
        kwargs["range_end"] = range_end

    try:
        with _create_workflow_progress(canonical_type) as (progress, task_id):
            def on_step(step_name, status, current, total):
                progress.update(task_id, completed=current, total=total,
                               description=f"[bold]{step_name}[/bold]")

            kwargs["progress_callback"] = on_step
            result = agent.run_workflow(molecule, canonical_type, method, basis, **kwargs)

        for step in result.steps:
            status = "[OK]" if step.status == "success" else "[FAIL]"
            console.print(f"{status} {step.description}")

        console.print(result.summary)

        from ..core.interpreter import ResultInterpreter
        interpreter = ResultInterpreter()
        interpretation = interpreter.interpret_workflow(result, molecule, method)
        console.print(interpretation)

        if HAS_PLT:
            try:
                if canonical_type == "method_comparison":
                    plot_method_comparison(result)
                elif canonical_type == "basis_convergence":
                    plot_basis_convergence(result)
            except Exception as e:
                console.print(f"Warning: plot generation failed: {e}", style="dim")

        if export:
            from ..workflows.export import export_to_json, export_to_csv
            wf_result = {"steps": [], "summary": result.summary, "success": result.success}
            for s in result.steps:
                wf_result["steps"].append({
                    "name": s.name, "description": s.description,
                    "status": s.status, "parsed": {k: str(v) for k, v in s.parsed.items()},
                })
            if export_format == "csv":
                export_to_csv(wf_result, export)
            else:
                export_to_json(wf_result, export)
            console.print(f"\nResults exported to {export} ({export_format.upper()})", style="dim")

    except Exception as e:
        console.print(f"Error: workflow failed: {str(e)}", style="red")


def _create_workflow_progress(workflow_type: str):
    """Create a Rich Progress context manager for workflow execution."""
    from contextlib import nullcontext
    try:
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
        )
        task_id = progress.add_task(f"Workflow: {workflow_type}", total=100)
        return _ProgressCtx(progress, task_id)
    except Exception:
        return nullcontext()


class _ProgressCtx:
    """Context wrapper for Rich Progress to allow clean 'with' usage."""
    def __init__(self, progress, task_id):
        self.progress = progress
        self.task_id = task_id

    def __enter__(self):
        self.progress.start()
        return self.progress, self.task_id

    def __exit__(self, *args):
        self.progress.stop()


@main.group()
def list():
    """List available computational resources."""
    pass


@list.command()
@click.option("--tag", "-t", help="Filter by tag")
@click.option("--search", "-s", help="Search molecules")
@click.option("--page", "-p", default=1, help="Page number")
@click.option("--page-size", "-n", default=20, help="Items per page")
def molecules(tag, search, page, page_size):
    """List available molecules."""
    if search:
        results = search_molecules(search)
        if not results:
            console.print(f"No molecules found matching '{search}'.", style="yellow")
            return
        console.print(f"\nSearch results for '{search}':", style="bold")
    else:
        if tag:
            results = list_molecules(tag=tag)
            console.print(f"\nMolecules with tag '{tag}':", style="bold")
        else:
            results = list_molecules()
            console.print("\nAvailable molecules:", style="bold")

    total = len(results)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(max(1, page), total_pages)
    start = (page - 1) * page_size
    end = min(start + page_size, total)
    page_items = results[start:end]

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Chinese")
    table.add_column("Formula")
    table.add_column("Electrons", justify="right")
    table.add_column("Charge", justify="right")
    table.add_column("Spin", justify="right")
    table.add_column("Tags")

    for mol in page_items:
        table.add_row(
            mol.name,
            mol.name_cn,
            mol.formula,
            str(mol.electrons or "?"),
            str(mol.charge),
            str(mol.spin),
            ", ".join(mol.tags[:3]),
        )

    console.print(table)
    if total_pages > 1:
        console.print(
            f"\nShowing {start+1}-{end} of {total} entries (page {page}/{total_pages}). "
            f"Use --page to navigate.",
            style="dim",
        )
    else:
        console.print(f"\nTotal: {total} molecules", style="dim")


@list.command()
def methods():
    """List available computational methods."""
    console.print("\nAvailable computational methods:", style="bold")

    console.print("\nDFT functionals:", style="cyan")
    categories = list_dft_categories()
    for cat in categories:
        funcs = list_dft_functionals(category=cat)
        if funcs:
            console.print(f"\n  [{cat}]", style="yellow")
            for f in funcs[:5]:
                console.print(f"    {f.name:<20} {f.name_cn}")
            if len(funcs) > 5:
                console.print(f"    ... and {len(funcs)} more functionals", style="dim")

    console.print("\nPost-HF methods:", style="cyan")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Method", style="cyan")
    table.add_column("Name (CN)")
    table.add_column("Scaling")
    table.add_column("Accuracy")

    for m in list_post_hf_methods():
        table.add_row(m.name, m.name_cn, m.cost_scaling, m.accuracy)
    console.print(table)

    console.print("\nExcited-state methods:", style="cyan")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Method", style="cyan")
    table.add_column("Name (CN)")
    table.add_column("Scaling")
    table.add_column("Accuracy")

    for m in list_excited_methods():
        table.add_row(m.name, m.name_cn, m.cost_scaling, m.accuracy)
    console.print(table)

    console.print("\nMulti-reference methods:", style="cyan")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Method", style="cyan")
    table.add_column("Name (CN)")
    table.add_column("Scaling")
    table.add_column("Accuracy")

    for m in list_multiref_methods():
        table.add_row(m.name, m.name_cn, m.cost_scaling, m.accuracy)
    console.print(table)

    console.print("\nRelativistic methods:", style="cyan")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Method", style="cyan")
    table.add_column("Name (CN)")
    table.add_column("Accuracy")
    table.add_column("Notes")

    for m in list_relativistic_methods():
        table.add_row(m.name, m.name_cn, m.accuracy, m.notes or m.description[:40])
    console.print(table)


@list.command()
@click.option("--category", "-c", help="Filter by category")
def basis(category):
    """List available basis sets."""
    if category:
        results = list_basis_sets(category=category)
        console.print(f"\nBasis sets in category '{category}':", style="bold")
    else:
        results = list_basis_sets()
        console.print("\nAvailable basis sets:", style="bold")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Level", justify="right")
    table.add_column("Category")

    for bs in results:
        table.add_row(bs.name, bs.description, str(bs.level), bs.category)
    console.print(table)


@list.command()
def solvents():
    """List available solvent models."""
    console.print("\nAvailable solvents:", style="bold")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Chinese")
    table.add_column("Dielectric", justify="right")
    table.add_column("Category")

    for s in list_solvents():
        table.add_row(s.name, s.name_cn, f"{s.dielectric:.2f}", s.category)
    console.print(table)


@list.command()
def tags():
    """List available molecule tags."""
    console.print("\nAvailable tags:", style="bold")
    for tag in list_tags():
        console.print(f"  - {tag}")


@list.command()
def aliases():
    """List workflow command aliases."""
    console.print("\nWorkflow aliases:", style="bold")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Alias", style="cyan")
    table.add_column("Canonical name")
    seen = set()
    for alias, canonical in sorted(WORKFLOW_ALIASES.items()):
        if canonical not in seen:
            table.add_row(alias, canonical)
            seen.add(canonical)
    console.print(table)


@main.command()
@click.argument("mol_name")
def xyz(mol_name):
    """Display XYZ coordinates for a molecule."""
    try:
        mol = get_molecule(mol_name)
        xyz_block = get_xyz_block(mol)
        console.print(f"\n{mol.name_cn} ({mol.formula}) XYZ coordinates:\n")
        console.print(Syntax(xyz_block, "xyz", theme="monokai"))
    except KeyError as e:
        console.print(str(e), style="red")


@main.command()
@click.argument("mol_name")
def info(mol_name):
    """Display detailed information about a molecule."""
    try:
        mol = get_molecule(mol_name)
        console.print(f"\n{mol.name_cn} ({mol.formula})", style="bold")

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        table.add_row("Name", mol.name)
        table.add_row("Chinese name", mol.name_cn)
        table.add_row("Formula", mol.formula)
        table.add_row("SMILES", mol.smiles)
        table.add_row("Electrons", str(mol.electrons or "unknown"))
        table.add_row("Charge", str(mol.charge))
        table.add_row("Spin", str(mol.spin))
        table.add_row("Multiplicity", str(mol.multiplicity))
        table.add_row("Symmetry", mol.symmetry)
        table.add_row("Atom count", str(mol.atom_count))
        table.add_row("Tags", ", ".join(mol.tags))

        console.print(table)

        console.print(f"\nXYZ coordinates:")
        console.print(Syntax(get_xyz_block(mol), "xyz", theme="monokai"))

    except KeyError as e:
        console.print(str(e), style="red")


@main.command()
@click.argument("filepath", type=str)
@click.option("--name", "-n", help="Molecule name (defaults to filename)")
@click.option("--charge", "-c", default=0, help="Charge")
@click.option("--spin", "-s", default=0, help="Number of unpaired electrons")
def import_mol(filepath, name, charge, spin):
    """Import a molecule from an XYZ file."""
    from ..molecules.sources import load_xyz_file, register_molecule
    from ..molecules.database import get_xyz_block

    mol = load_xyz_file(filepath)
    if not mol:
        console.print(f"Error: unable to load file: {filepath}", style="red")
        return

    if name:
        mol.name = name.lower().replace(" ", "_")
        mol.name_cn = name
    if charge:
        mol.charge = charge
    if spin:
        mol.spin = spin

    register_molecule(mol)

    console.print(f"\n[OK] Molecule imported:", style="green bold")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Property", style="cyan")
    table.add_column("Value")
    table.add_row("Name", mol.name)
    table.add_row("Formula", mol.formula)
    table.add_row("Atom count", str(mol.atom_count))
    table.add_row("Electrons", str(mol.electrons or "?"))
    table.add_row("Charge", str(mol.charge))
    table.add_row("Spin", str(mol.spin))
    console.print(table)

    console.print(f"\nXYZ coordinates:")
    console.print(Syntax(get_xyz_block(mol), "xyz", theme="monokai"))
    console.print(f"\nNow available as: '{mol.name}'", style="dim")


@main.command()
@click.argument("name", nargs=-1, type=str)
def search(name):
    """Search PubChem for a molecule by name."""
    if not name:
        console.print("Please provide a molecule name to search.", style="red")
        return

    query = " ".join(name)
    console.print(f"\nSearching PubChem for '{query}'...", style="bold")

    from ..molecules.sources import search_pubchem, register_molecule
    from ..molecules.database import get_xyz_block

    mol = search_pubchem(query)
    if not mol:
        console.print(f"Error: '{query}' not found in PubChem.", style="red")
        console.print("Verify spelling, or try the English/IUPAC name.", style="dim")
        return

    register_molecule(mol)

    console.print(f"\n[OK] Molecule found:", style="green bold")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Property", style="cyan")
    table.add_column("Value")
    table.add_row("Name", mol.name)
    table.add_row("IUPAC name", mol.name_cn)
    table.add_row("Formula", mol.formula)
    table.add_row("SMILES", mol.smiles)
    table.add_row("Atom count", str(mol.atom_count))
    table.add_row("Electrons", str(mol.electrons or "?"))
    table.add_row("Source", ", ".join(mol.tags))
    console.print(table)

    console.print(f"\n3D coordinates:")
    console.print(Syntax(get_xyz_block(mol), "xyz", theme="monokai"))
    console.print(f"\nNow available as: '{mol.name}'", style="dim")


@main.command()
def version():
    """Display the Frank version."""
    from .. import __version__
    console.print(f"Frank v{__version__}", style="bold cyan")
    console.print("Computational Chemistry Terminal Agent")
    console.print("Code generation | Execution | Diagnostics | Interpretation")


def interactive_mode(classic: bool = False):
    """Run the Frank interactive REPL with readline support and session state."""
    print_banner()

    # Check first-run onboarding
    from ..config import is_first_run, mark_onboarded
    if is_first_run():
        console.print()
        _print_onboarding()
        mark_onboarded()

    # Initialize readline for command history and tab completion
    _setup_readline()

    console.print("\nEnter a computational chemistry query. Type 'help' for usage, 'quit' to exit.")
    console.print("  Prefix with 'run' to execute; without prefix, generates code only.")
    console.print("  Prefix with 'plan' to design workflows, 'auto' to run complex workflows.")
    console.print("  Prefix with 'explain' to ask method/workflow questions.")
    console.print("  Prefix with 'search <name>' to query PubChem, 'import <file>' to load XYZ.\n")

    agent = create_agent(classic=classic)

    while True:
        try:
            text = Prompt.ask("[bold cyan]Frank[/bold cyan]")

            if not text.strip():
                continue

            if text.lower() in ["quit", "exit", "q"]:
                _save_readline_history()
                console.print("Session ended.", style="bold")
                break

            if text.lower() in ["help", "h"]:
                console.print(agent.get_help())
                continue

            if text.lower() in ["clear", "cls"]:
                console.clear()
                print_banner()
                continue

            if text.lower() == "session":
                _show_session(agent)
                continue

            if text.lower().startswith("import "):
                _handle_import(text[7:].strip())
                continue

            if text.lower().startswith("search "):
                _handle_search(text[7:].strip())
                continue

            # Inline workflow aliases
            if text.lower().startswith("compare "):
                _handle_inline_workflow(agent, text[8:].strip(), "method_comparison")
                continue

            if text.lower().startswith("converge "):
                _handle_inline_workflow(agent, text[9:].strip(), "basis_convergence")
                continue

            if text.lower().startswith("batch "):
                _handle_inline_batch(agent, text[6:].strip())
                continue

            if text.lower().startswith("plan "):
                wf_plan = agent.plan_workflow(text[5:].strip())
                print_workflow_plan(wf_plan)
                continue

            if text.lower().startswith("auto "):
                console.print("\nExecuting autonomous workflow...", style="bold")
                result = agent.run_autonomous(text[5:].strip())
                print_autonomous_result(result, agent=agent)
                continue

            if text.lower().startswith("explain "):
                answer = agent.explain(text[8:].strip())
                console.print(Markdown(answer))
                continue

            if text.lower().startswith("run "):
                text = text[4:].strip()
                console.print(f"\nExecuting calculation...", style="bold")
                result = agent.run(text)
                if result["code"]:
                    console.print("\nGenerated code:", style="bold")
                    script = result["script"]
                    syntax = Syntax(script[:2000] + "\n..." if len(script) > 2000 else script,
                                   "python", theme="monokai", line_numbers=True)
                    console.print(Panel(syntax, title=result["code"].title, border_style="green"))
                print_execution_result(result)
            else:
                result = agent.process_request(text)
                if result.get("is_chat"):
                    console.print(f"\n{result['chat_message']}\n")
                    continue
                print_code_result(result)
                # Offer inline correction
                if result.get("code") and result.get("intent"):
                    _offer_correction(agent, result)

        except KeyboardInterrupt:
            _save_readline_history()
            console.print("\nSession ended.", style="bold")
            break
        except Exception as e:
            console.print(f"Error: {str(e)}", style="red")


def _setup_readline():
    """Configure readline for command history and tab completion."""
    try:
        import readline
        hist_dir = os.path.expanduser("~/.frank")
        os.makedirs(hist_dir, exist_ok=True)
        hist_file = os.path.join(hist_dir, "history")
        readline.set_history_length(1000)
        try:
            readline.read_history_file(hist_file)
        except FileNotFoundError:
            pass
        from .completion import FrankCompleter
        readline.set_completer(FrankCompleter().complete)
        readline.parse_and_bind("tab: complete")
    except ImportError:
        pass


def _save_readline_history():
    """Persist readline history to disk."""
    try:
        import readline
        hist_file = os.path.expanduser("~/.frank/history")
        readline.write_history_file(hist_file)
    except (ImportError, OSError):
        pass


def _print_onboarding():
    """Display first-run onboarding guide."""
    console.print("Welcome to Frank -- Computational Chemistry Terminal Agent", style="bold")
    console.print()
    console.print("Frank generates and executes PySCF quantum chemistry calculations from")
    console.print("natural language descriptions. It supports Hartree-Fock, DFT, MP2, CCSD(T),")
    console.print("TDDFT, CASSCF, solvent models, and multi-step workflows.")
    console.print()
    console.print("Quick start examples:", style="bold")
    console.print('  frank ask "Calculate the energy of water at B3LYP/6-31G* level"')
    console.print('  frank run "Optimize benzene geometry with wB97X-D/def2-SVP"')
    console.print('  frank workflow opt_freq ethanol --method B3LYP --basis 6-31G*')
    console.print('  frank search caffeine')
    console.print('  frank import molecule.xyz --name mymol')
    console.print()
    console.print("Interactive mode commands:", style="bold")
    console.print("  run <query>       Execute calculation")
    console.print("  search <name>     Query PubChem database")
    console.print("  import <file>     Load XYZ file")
    console.print("  compare <mol> <methods>  Parallel method comparison")
    console.print("  converge <mol> <basis_sets>  Basis set convergence test")
    console.print("  plan <query>      Design multi-step workflow (no execution)")
    console.print("  auto <query>      Autonomously plan and execute complex workflow")
    console.print("  explain <question>  Query method/workflow knowledge")
    console.print("  help              Show full help")
    console.print("  session           Display current session state")
    console.print("  quit              Exit")
    console.print()
    console.print("For a complete reference, type 'help' at the Frank prompt.", style="dim")


def _show_session(agent: FrankAgent):
    """Display current session context."""
    ctx = agent.session
    console.print("\nSession context:", style="bold")
    if not ctx.last_molecule:
        console.print("  (empty -- no calculations performed yet)", style="dim")
        return
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Parameter", style="cyan")
    table.add_column("Value")
    if ctx.last_molecule:
        table.add_row("Last molecule", ctx.last_molecule)
    if ctx.last_method:
        table.add_row("Last method", ctx.last_method)
    if ctx.last_basis:
        table.add_row("Last basis set", ctx.last_basis)
    if ctx.last_calc_type:
        table.add_row("Last calculation", ctx.last_calc_type)
    if ctx.recent_molecules:
        table.add_row("Recent molecules", ", ".join(ctx.recent_molecules))
    console.print(table)


def _offer_correction(agent: FrankAgent, result: dict):
    """Offer the user a chance to correct the parsed intent."""
    console.print()
    choice = Prompt.ask(
        "Proceed with these parameters?",
        choices=["y", "n", "edit"],
        default="y",
    )
    if choice == "n":
        console.print("Request cancelled.", style="yellow")
        return
    if choice == "edit":
        intent = result["intent"]
        overrides = {}
        new_mol = Prompt.ask("  Molecule", default=intent.molecule or "")
        if new_mol and new_mol != intent.molecule:
            overrides["molecule"] = new_mol
        new_method = Prompt.ask("  Method", default=intent.method or "")
        if new_method and new_method != intent.method:
            overrides["method"] = new_method
        new_basis = Prompt.ask("  Basis set", default=intent.basis or "")
        if new_basis and new_basis != intent.basis:
            overrides["basis"] = new_basis
        new_calc = Prompt.ask("  Calculation type", default=intent.calc_type or "")
        if new_calc and new_calc != intent.calc_type:
            overrides["calc_type"] = new_calc
        new_solvent = Prompt.ask("  Solvent", default=intent.solvent or "")
        if new_solvent and new_solvent != intent.solvent:
            overrides["solvent"] = new_solvent
        new_nstates = Prompt.ask("  Excited states", default=str(intent.n_states or ""))
        if new_nstates and new_nstates != str(intent.n_states or ""):
            try:
                overrides["n_states"] = int(new_nstates)
            except ValueError:
                pass

        if overrides:
            adjusted = agent.adjust_intent(intent, overrides)
            try:
                code = agent.generate_code(adjusted)
                script = code.to_script()
                console.print("\nRevised code:", style="bold")
                syntax = Syntax(script, "python", theme="monokai", line_numbers=True)
                console.print(Panel(syntax, title=code.title, border_style="green"))
            except Exception as e:
                console.print(f"Error generating code: {str(e)}", style="red")


def _handle_import(filepath: str):
    """Handle 'import <file>' command in interactive mode."""
    from ..molecules.sources import load_xyz_file, register_molecule
    mol = load_xyz_file(filepath)
    if mol:
        register_molecule(mol)
        console.print(
            f"[OK] Imported: {mol.name_cn} ({mol.formula}), {mol.atom_count} atoms",
            style="green",
        )
    else:
        console.print(f"Error: unable to load file: {filepath}", style="red")


def _handle_search(query: str):
    """Handle 'search <query>' command in interactive mode."""
    console.print(f"Searching PubChem for '{query}'...", style="bold")
    from ..molecules.sources import search_pubchem, register_molecule
    mol = search_pubchem(query)
    if mol:
        register_molecule(mol)
        console.print(
            f"[OK] Found: {mol.name_cn} ({mol.formula}), SMILES: {mol.smiles}",
            style="green",
        )
        console.print(f"   Atoms: {mol.atom_count}, Electrons: {mol.electrons}", style="dim")
        console.print(f"   Now available as: '{mol.name}'", style="dim")
    else:
        console.print(f"Error: '{query}' not found in PubChem.", style="red")


def _handle_inline_workflow(agent: FrankAgent, args: str, workflow_type: str):
    """Handle inline workflow commands (compare, converge) in interactive mode."""
    parts = args.split()
    if workflow_type == "method_comparison":
        if len(parts) >= 2:
            molecule = parts[0]
            methods = parts[1].split(",")
            basis = parts[2] if len(parts) > 2 else "6-31g*"
            console.print(f"\nRunning method comparison on {molecule}...", style="bold")
            result = agent.run_workflow(molecule, "method_comparison", methods=methods, basis=basis)
            console.print(result.summary)
        else:
            console.print("Usage: compare <molecule> <method1,method2,...> [basis]", style="yellow")
    elif workflow_type == "basis_convergence":
        if len(parts) >= 2:
            molecule = parts[0]
            basis_sets = parts[1].split(",")
            method = parts[2] if len(parts) > 2 else "B3LYP"
            console.print(f"\nRunning basis set convergence on {molecule}...", style="bold")
            result = agent.run_workflow(molecule, "basis_convergence", method=method, basis_sets=basis_sets)
            console.print(result.summary)
        else:
            console.print("Usage: converge <molecule> <basis1,basis2,...> [method]", style="yellow")


def _handle_inline_batch(agent: FrankAgent, args: str):
    """Handle 'batch' command in interactive mode."""
    parts = args.split()
    if len(parts) >= 1:
        molecules = parts[0].split(",")
        method = parts[1] if len(parts) > 1 else "B3LYP"
        basis = parts[2] if len(parts) > 2 else "6-31g*"
        console.print(f"\nRunning batch calculation on {len(molecules)} molecules...", style="bold")
        try:
            from ..aio.agent import AsyncFrankAgent
            import asyncio
            async def _run():
                a_agent = AsyncFrankAgent()
                result = await a_agent.run_multi_molecule(molecules, method, basis)
                console.print(result.summary)
            asyncio.run(_run())
        except Exception as e:
            console.print(f"Error: {str(e)}", style="red")
    else:
        console.print("Usage: batch <mol1,mol2,...> [method] [basis]", style="yellow")


if __name__ == "__main__":
    main()
