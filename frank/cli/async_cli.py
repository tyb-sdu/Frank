"""
Async CLI -- asynchronous command-line interface for Frank.

Features:
1. Non-blocking asynchronous calculation execution
2. Real-time progress output
3. Parallel workflow execution
4. Cancellation support (Ctrl+C)
"""

import asyncio
import os
import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.live import Live
from rich.text import Text
from rich.prompt import Prompt

from .. import __version__
from ..aio.agent import AsyncFrankAgent
from ..aio.executor import AsyncTask, TaskStatus, format_task_status, format_tasks_table
from ..molecules.database import list_molecules, get_molecule, search_molecules, get_xyz_block
from ..core.diagnostics import format_diagnostics


console = Console()


def print_banner():
    """Print a clean, academic-style banner."""
    banner = f"Frank -- Computational Chemistry Terminal Agent v{__version__} (async)"
    console.print(banner, style="bold cyan")
    console.print("Async execution | Parallel computation | Real-time progress", style="dim")


def print_task_result(task: AsyncTask, interpretation: str = ""):
    """Display task execution result."""
    if task.success:
        console.print(f"\n[OK] Calculation succeeded (duration {task.duration:.1f} s)", style="green")

        if task.stdout:
            lines = task.stdout.strip().split("\n")
            output_lines = [l for l in lines if not l.startswith("_FRANK_")]
            if output_lines:
                console.print("\nStandard output:", style="dim")
                for line in output_lines[-20:]:
                    console.print(f"  {line}", style="dim")
    else:
        console.print(f"\n[FAIL] Calculation failed", style="red")
        if task.error_type:
            console.print(f"   Error type: {task.error_type}")
        if task.error_message:
            console.print(f"   Error message: {task.error_message}")

    if interpretation:
        console.print(interpretation)


# ============================================================
#  CLI 命令
# ============================================================

@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Frank -- Computational Chemistry Terminal Agent (async edition)"""
    if ctx.invoked_subcommand is None:
        asyncio.run(interactive_mode())


@main.command()
@click.argument("query", nargs=-1, type=str)
@click.option("--no-interpret", is_flag=True, help="Skip result interpretation")
@click.option("--timeout", "-t", default=600, help="Timeout in seconds")
@click.option("--export", "-e", default=None, help="Export results to file")
@click.option("--export-format", default="json", type=click.Choice(["json", "csv"]), help="Export format")
def run(query, no_interpret, timeout, export, export_format):
    """Execute calculation asynchronously."""
    if not query:
        console.print("Please provide a calculation request.", style="red")
        return

    text = " ".join(query)

    async def _run():
        agent = AsyncFrankAgent(timeout=timeout)

        console.print(f"\nExecuting calculation...", style="bold")

        result = await agent.run(text, interpret=not no_interpret)

        if result["code"]:
            console.print("\nGenerated code:", style="bold")
            script = result["script"]
            syntax = Syntax(script[:2000] + "\n..." if len(script) > 2000 else script,
                           "python", theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title=result["code"].title, border_style="green"))

        task = result.get("task")
        if task:
            print_task_result(task, result.get("interpretation", ""))

        if export and task:
            from ..workflows.export import export_to_json, export_to_csv
            export_data = {"task": {"success": task.success, "duration": task.duration}, "parsed": result.get("parsed", {})}
            if export_format == "csv":
                export_to_csv(export_data, export)
            else:
                export_to_json(export_data, export)
            console.print(f"\nResults exported to {export} ({export_format.upper()})", style="dim")

    asyncio.run(_run())


@main.command()
@click.argument("molecule")
@click.option("--methods", "-m", default="HF,B3LYP,MP2", help="Method list (comma-separated)")
@click.option("--basis", "-b", default="6-31g*", help="Basis set")
@click.option("--timeout", "-t", default=600, help="Timeout in seconds")
@click.option("--max-parallel", "-p", default=4, help="Maximum parallel tasks")
def compare(molecule, methods, basis, timeout, max_parallel):
    """Parallel method comparison."""
    methods_list = [m.strip() for m in methods.split(",")]

    async def _compare():
        agent = AsyncFrankAgent(timeout=timeout, max_parallel=max_parallel)

        console.print(f"\nRunning parallel comparison of {len(methods_list)} methods...", style="bold")

        result = await agent.run_method_comparison(molecule, methods_list, basis)

        console.print(result.summary)

    asyncio.run(_compare())


@main.command()
@click.argument("molecule")
@click.option("--method", "-m", default="B3LYP", help="Computational method")
@click.option("--basis-sets", "-b", default="6-31g*,cc-pvdz,cc-pvtz", help="Basis set list (comma-separated)")
@click.option("--timeout", "-t", default=600, help="Timeout in seconds")
@click.option("--max-parallel", "-p", default=4, help="Maximum parallel tasks")
def converge(molecule, method, basis_sets, timeout, max_parallel):
    """Parallel basis set convergence test."""
    basis_list = [b.strip() for b in basis_sets.split(",")]

    async def _converge():
        agent = AsyncFrankAgent(timeout=timeout, max_parallel=max_parallel)

        console.print(f"\nRunning parallel convergence test with {len(basis_list)} basis sets...", style="bold")

        result = await agent.run_basis_convergence(molecule, method, basis_list)

        console.print(result.summary)

    asyncio.run(_converge())


@main.command()
@click.argument("molecules", nargs=-1, type=str)
@click.option("--method", "-m", default="B3LYP", help="Computational method")
@click.option("--basis", "-b", default="6-31g*", help="Basis set")
@click.option("--timeout", "-t", default=600, help="Timeout in seconds")
@click.option("--max-parallel", "-p", default=4, help="Maximum parallel tasks")
def batch(molecules, method, basis, timeout, max_parallel):
    """Parallel batch calculation on multiple molecules."""
    if not molecules:
        console.print("Please specify molecule names.", style="red")
        return

    async def _batch():
        agent = AsyncFrankAgent(timeout=timeout, max_parallel=max_parallel)

        console.print(f"\nRunning parallel calculation on {len(molecules)} molecules...", style="bold")

        result = await agent.run_multi_molecule(list(molecules), method, basis)

        console.print(result.summary)

    asyncio.run(_batch())


@main.command()
def tasks():
    """Display all task statuses."""
    async def _tasks():
        agent = AsyncFrankAgent()
        all_tasks = agent.get_all_tasks()

        if not all_tasks:
            console.print("No active tasks.", style="dim")
        else:
            console.print(format_tasks_table(all_tasks))

    asyncio.run(_tasks())


# ============================================================
#  交互模式
# ============================================================

async def interactive_mode():
    """Asynchronous interactive REPL mode."""
    print_banner()

    # Check first-run onboarding
    from ..config import is_first_run, mark_onboarded
    if is_first_run():
        console.print()
        console.print("Welcome to Frank -- Computational Chemistry Terminal Agent (async edition)", style="bold")
        console.print()
        console.print("Async mode adds parallel execution, real-time progress, and task cancellation.")
        console.print("Supported prefixes: 'run' (execute), 'compare' (parallel method comparison),")
        console.print("'converge' (basis set convergence), 'batch' (multi-molecule calculation).")
        console.print()
        console.print("Type 'help' for complete usage information.", style="dim")
        mark_onboarded()

    # Initialize readline
    _setup_async_readline()

    console.print("\nEnter a computational chemistry query. Type 'help' for usage, 'quit' to exit.")
    console.print("  Prefix with 'run' to execute, 'compare' for method comparison,")
    console.print("  'converge' for basis set convergence, 'batch' for multi-molecule.\n")

    agent = AsyncFrankAgent()

    while True:
        try:
            text = await asyncio.get_event_loop().run_in_executor(
                None, lambda: Prompt.ask("[bold cyan]Frank[/bold cyan]")
            )

            if not text.strip():
                continue

            if text.lower() in ["quit", "exit", "q"]:
                _save_async_readline_history()
                await agent.cancel_all()
                console.print("Session ended.", style="bold")
                break

            if text.lower() in ["help", "h"]:
                console.print(agent.get_help())
                continue

            if text.lower() in ["clear", "cls"]:
                console.clear()
                print_banner()
                continue

            if text.lower() == "tasks":
                all_tasks = agent.get_all_tasks()
                if all_tasks:
                    console.print(format_tasks_table(all_tasks))
                else:
                    console.print("No active tasks.", style="dim")
                continue

            if text.lower() == "session":
                console.print("Session state tracking available in the synchronous (non-async) interactive mode.", style="dim")
                continue

            if text.lower().startswith("search "):
                query = text[7:].strip()
                console.print(f"Searching PubChem for '{query}'...", style="bold")
                from ..molecules.sources import search_pubchem, register_molecule
                mol = search_pubchem(query)
                if mol:
                    register_molecule(mol)
                    console.print(f"[OK] Found: {mol.name_cn} ({mol.formula}), SMILES: {mol.smiles}", style="green")
                    console.print(f"   Now available as: '{mol.name}'", style="dim")
                else:
                    console.print(f"Error: '{query}' not found in PubChem.", style="red")
                continue

            if text.lower().startswith("import "):
                filepath = text[7:].strip()
                from ..molecules.sources import load_xyz_file, register_molecule
                mol = load_xyz_file(filepath)
                if mol:
                    register_molecule(mol)
                    console.print(f"[OK] Imported: {mol.name_cn} ({mol.formula}), {mol.atom_count} atoms", style="green")
                else:
                    console.print(f"Error: unable to load file: {filepath}", style="red")
                continue

            # Parallel method comparison
            if text.lower().startswith("compare "):
                parts = text[8:].strip().split()
                if len(parts) >= 2:
                    molecule = parts[0]
                    methods = [m.strip() for m in parts[1].split(",")]
                    basis = parts[2] if len(parts) > 2 else "6-31g*"

                    console.print(f"\nRunning parallel comparison of {len(methods)} methods...", style="bold")
                    result = await agent.run_method_comparison(molecule, methods, basis)
                    console.print(result.summary)
                else:
                    console.print("Usage: compare <molecule> <method1,method2,...> [basis]", style="yellow")
                continue

            # Basis set convergence
            if text.lower().startswith("converge "):
                parts = text[9:].strip().split()
                if len(parts) >= 2:
                    molecule = parts[0]
                    basis_sets = [b.strip() for b in parts[1].split(",")]
                    method = parts[2] if len(parts) > 2 else "B3LYP"

                    console.print(f"\nRunning parallel convergence test with {len(basis_sets)} basis sets...", style="bold")
                    result = await agent.run_basis_convergence(molecule, method, basis_sets)
                    console.print(result.summary)
                else:
                    console.print("Usage: converge <molecule> <basis1,basis2,...> [method]", style="yellow")
                continue

            # Batch calculation
            if text.lower().startswith("batch "):
                parts = text[6:].strip().split()
                if len(parts) >= 1:
                    molecules = [m.strip() for m in parts[0].split(",")]
                    method = parts[1] if len(parts) > 1 else "B3LYP"
                    basis = parts[2] if len(parts) > 2 else "6-31g*"

                    console.print(f"\nRunning parallel calculation on {len(molecules)} molecules...", style="bold")
                    result = await agent.run_multi_molecule(molecules, method, basis)
                    console.print(result.summary)
                else:
                    console.print("Usage: batch <mol1,mol2,...> [method] [basis]", style="yellow")
                continue

            # Normal calculation
            if text.lower().startswith("run "):
                text = text[4:].strip()

            console.print(f"\nExecuting calculation...", style="bold")

            def on_output(line):
                if "converged" in line.lower() or "energy" in line.lower():
                    console.print(f"  {line}", style="dim")

            result = await agent.run_with_streaming(text, on_output=on_output)

            if result.get("code"):
                console.print("\nGenerated code:", style="bold")
                script = result["script"]
                syntax = Syntax(script[:1500] + "\n..." if len(script) > 1500 else script,
                               "python", theme="monokai", line_numbers=True)
                console.print(Panel(syntax, title=result["code"].title, border_style="green"))

            task = result.get("task")
            if task:
                parsed = result.get("parsed", {})
                interpretation = ""
                if parsed:
                    from ..core.interpreter import ResultInterpreter
                    interpreter = ResultInterpreter()
                    if "scf" in parsed:
                        interpretation = interpreter.interpret_scf(
                            parsed["scf"],
                            method=result["intent"].method or "HF",
                            mol_name=get_molecule(result["intent"].molecule).name_cn,
                        )

                print_task_result(task, interpretation)

        except KeyboardInterrupt:
            _save_async_readline_history()
            await agent.cancel_all()
            console.print("\nAll tasks cancelled.", style="yellow")
            continue
        except Exception as e:
            console.print(f"Error: {str(e)}", style="red")


def _setup_async_readline():
    """Configure readline for the async interactive prompt."""
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


def _save_async_readline_history():
    """Persist readline history to disk."""
    try:
        import readline
        hist_file = os.path.expanduser("~/.frank/history")
        readline.write_history_file(hist_file)
    except (ImportError, OSError):
        pass


if __name__ == "__main__":
    main()
