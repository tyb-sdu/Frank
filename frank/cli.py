import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.text import Text

from .agent import FrankAgent
from .molecules import list_molecules, get_molecule, search_molecules, get_xyz_block, list_tags
from .basis_sets import list_basis_sets
from .methods.dft import list_dft_functionals, list_dft_categories
from .methods.post_hf import list_post_hf_methods
from .methods.excited import list_excited_methods
from .methods.relativistic import list_relativistic_methods
from .methods.casscf import list_multiref_methods
from .methods.solvation import list_solvents, list_solvation_models
from .diagnostics import format_diagnostics
from .visualizer import plot_result, plot_method_comparison, plot_basis_convergence, HAS_PLT


console = Console()


def print_banner():
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ███████╗██████╗  █████╗ ███╗   ██╗██╗  ██╗              ║
║     ██╔════╝██╔══██╗██╔══██╗████╗  ██║██║ ██╔╝              ║
║     █████╗  ██████╔╝███████║██╔██╗ ██║█████╔╝               ║
║     ██╔══╝  ██╔══██╗██╔══██║██║╚██╗██║██╔═██╗               ║
║     ██║     ██║  ██║██║  ██║██║ ╚████║██║  ██╗              ║
║     ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝              ║
║                                                              ║
║          计算化学终端智能体 v0.2.0                             ║
║          能生成、能执行、能诊断、能解读                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="bold cyan")


def print_code_result(result: dict):
    if result.get("is_chat"):
        console.print(f"\n{result['chat_message']}\n")
        return

    intent = result["intent"]
    code = result["code"]
    warnings = result["warnings"]

    if warnings:
        for w in warnings:
            console.print(f"[WARN]  {w}", style="yellow")

    if not code:
        console.print("[FAIL] 无法生成代码，请检查输入", style="red")
        return

    console.print("\n解析结果:", style="bold")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("项目", style="cyan")
    table.add_column("值")

    if intent.molecule:
        try:
            mol = get_molecule(intent.molecule)
            table.add_row("分子", f"{mol.name_cn} ({mol.formula})")
        except:
            table.add_row("分子", intent.molecule)

    if intent.method:
        table.add_row("方法", intent.method)
    if intent.basis:
        table.add_row("基组", intent.basis)
    if intent.calc_type:
        type_names = {
            "energy": "单点能",
            "geometry": "几何优化",
            "frequency": "频率计算",
            "excited": "激发态",
            "casscf": "CASSCF",
            "nbo": "NBO 分析",
        }
        table.add_row("计算类型", type_names.get(intent.calc_type, intent.calc_type))
    if intent.solvent:
        table.add_row("溶剂", intent.solvent)
    if intent.n_states:
        table.add_row("激发态数", str(intent.n_states))
    if intent.norb and intent.nelec:
        table.add_row("活性空间", f"({intent.norb}, {intent.nelec})")

    console.print(table)

    conf = intent.confidence
    conf_color = "green" if conf > 0.7 else "yellow" if conf > 0.4 else "red"
    console.print(f"\n解析置信度: {conf:.0%}", style=conf_color)

    console.print("\n生成的代码:", style="bold")
    script = code.to_script()
    syntax = Syntax(script, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=code.title, border_style="green"))

    if code.run_instructions:
        console.print(f"\n运行方式: {code.run_instructions}", style="bold")


def print_execution_result(result: dict, show_plot: bool = True):
    execution = result.get("execution")
    parsed = result.get("parsed", {})
    diagnostics = result.get("diagnostics", [])
    interpretation = result.get("interpretation", "")

    if not execution:
        console.print("[FAIL] 未执行计算", style="red")
        return

    retry_log = result.get("retry_log", [])
    if retry_log:
        console.print("\n自动恢复日志:", style="bold yellow")
        for entry in retry_log:
            console.print(f"   {entry}")

    if execution.success:
        console.print(f"\n[OK] 计算成功 (耗时 {execution.duration:.1f} 秒)", style="green")
    else:
        console.print(f"\n[FAIL] 计算失败", style="red")
        if execution.error_type:
            console.print(f"   错误类型: {execution.error_type}")
        if execution.error_message:
            console.print(f"   错误信息: {execution.error_message}")

    if diagnostics:
        console.print("\n诊断结果:", style="bold")
        console.print(format_diagnostics(diagnostics))

    if interpretation:
        console.print(interpretation)

    if show_plot and parsed and HAS_PLT:
        try:
            plot_result(parsed)
        except Exception as e:
            console.print(f"[WARN] 图表绘制失败: {e}", style="dim")

    if execution.stdout:
        console.print("\n计算输出:", style="dim")
        lines = execution.stdout.strip().split("\n")
        for line in lines[-20:]:
            console.print(f"  {line}", style="dim")


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    if ctx.invoked_subcommand is None:
        interactive_mode()


@main.command()
@click.argument("query", nargs=-1, type=str)
def ask(query):
    if not query:
        console.print("请输入计算需求", style="red")
        return

    text = " ".join(query)
    agent = FrankAgent()
    result = agent.process_request(text)
    print_code_result(result)


@main.command()
@click.argument("query", nargs=-1, type=str)
@click.option("--no-interpret", is_flag=True, help="不解读结果")
@click.option("--no-plot", is_flag=True, help="不显示图表")
@click.option("--timeout", "-t", default=600, help="超时时间（秒）")
def run(query, no_interpret, no_plot, timeout):
    if not query:
        console.print("请输入计算需求", style="red")
        return

    text = " ".join(query)
    console.print(f"\n正在执行计算...", style="bold")

    agent = FrankAgent(timeout=timeout)
    result = agent.run(text, interpret=not no_interpret)

    if result["code"]:
        console.print("\n生成的代码:", style="bold")
        script = result["script"]
        syntax = Syntax(script[:2000] + "\n..." if len(script) > 2000 else script,
                       "python", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=result["code"].title, border_style="green"))

    show_plot = not no_plot
    print_execution_result(result, show_plot=show_plot)


@main.command()
@click.argument("workflow_type", type=click.Choice([
    "opt_freq", "method_comparison", "basis_convergence",
    "pes_scan", "solvation",
]))
@click.argument("molecule")
@click.option("--method", "-m", default="B3LYP", help="计算方法")
@click.option("--basis", "-b", default="6-31g*", help="基组")
@click.option("--methods", help="方法列表（逗号分隔）")
@click.option("--basis-sets", help="基组列表（逗号分隔）")
@click.option("--solvent", default="water", help="溶剂（用于溶剂化工作流）")
@click.option("--scan-type", default="bond", help="扫描类型（bond/angle/dihedral）")
@click.option("--atoms", default="0,1", help="扫描原子索引（逗号分隔）")
@click.option("--n-points", default=11, type=int, help="扫描点数")
@click.option("--range-start", default=0.8, type=float, help="扫描起始值")
@click.option("--range-end", default=2.0, type=float, help="扫描终止值")
@click.option("--timeout", "-t", default=600, help="超时时间（秒）")
def workflow(workflow_type, molecule, method, basis, methods, basis_sets,
             solvent, scan_type, atoms, n_points, range_start, range_end, timeout):
    console.print(f"\n正在运行工作流: {workflow_type}...", style="bold")

    agent = FrankAgent(timeout=timeout)

    kwargs = {}
    if methods:
        kwargs["methods"] = methods.split(",")
    if basis_sets:
        kwargs["basis_sets"] = basis_sets.split(",")
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
        result = agent.run_workflow(molecule, workflow_type, method, basis, **kwargs)

        for step in result.steps:
            status = "[OK]" if step.status == "success" else "[FAIL]"
            console.print(f"{status} {step.description}")

        console.print(result.summary)

        from .interpreter import ResultInterpreter
        interpreter = ResultInterpreter()
        interpretation = interpreter.interpret_workflow(result, molecule, method)
        console.print(interpretation)

        if HAS_PLT:
            try:
                if workflow_type == "method_comparison":
                    plot_method_comparison(result)
                elif workflow_type == "basis_convergence":
                    plot_basis_convergence(result)
            except Exception as e:
                console.print(f"[WARN] 图表绘制失败: {e}", style="dim")

    except Exception as e:
        console.print(f"[FAIL] 工作流失败: {str(e)}", style="red")


@main.group()
def list():
    pass


@list.command()
@click.option("--tag", "-t", help="按标签筛选")
@click.option("--search", "-s", help="搜索分子")
def molecules(tag, search):
    if search:
        results = search_molecules(search)
        if not results:
            console.print(f"未找到匹配 '{search}' 的分子", style="yellow")
            return
        console.print(f"\n搜索 '{search}' 的结果:", style="bold")
    else:
        if tag:
            results = list_molecules(tag=tag)
            console.print(f"\n标签为 '{tag}' 的分子:", style="bold")
        else:
            results = list_molecules()
            console.print("\n所有可用分子:", style="bold")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("名称", style="cyan")
    table.add_column("中文名")
    table.add_column("分子式")
    table.add_column("电子数", justify="right")
    table.add_column("电荷", justify="right")
    table.add_column("自旋", justify="right")
    table.add_column("标签")

    for mol in results:
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
    console.print(f"\n共 {len(results)} 个分子", style="dim")


@list.command()
def methods():
    console.print("\n可用的计算方法:", style="bold")

    console.print("\nDFT 泛函:", style="cyan")
    categories = list_dft_categories()
    for cat in categories:
        funcs = list_dft_functionals(category=cat)
        if funcs:
            console.print(f"\n  [{cat}]", style="yellow")
            for f in funcs[:5]:
                console.print(f"    {f.name:<20} {f.name_cn}")
            if len(funcs) > 5:
                console.print(f"    ... 等 {len(funcs)} 个泛函", style="dim")

    console.print("\n后 HF 方法:", style="cyan")
    table = Table(show_header=True, header_style="bold")
    table.add_column("方法", style="cyan")
    table.add_column("中文名")
    table.add_column("计算标度")
    table.add_column("精度")

    for m in list_post_hf_methods():
        table.add_row(m.name, m.name_cn, m.cost_scaling, m.accuracy)
    console.print(table)

    console.print("\n激发态方法:", style="cyan")
    table = Table(show_header=True, header_style="bold")
    table.add_column("方法", style="cyan")
    table.add_column("中文名")
    table.add_column("计算标度")
    table.add_column("精度")

    for m in list_excited_methods():
        table.add_row(m.name, m.name_cn, m.cost_scaling, m.accuracy)
    console.print(table)

    console.print("\n多参考态方法:", style="cyan")
    table = Table(show_header=True, header_style="bold")
    table.add_column("方法", style="cyan")
    table.add_column("中文名")
    table.add_column("计算标度")
    table.add_column("精度")

    for m in list_multiref_methods():
        table.add_row(m.name, m.name_cn, m.cost_scaling, m.accuracy)
    console.print(table)

    console.print("\n相对论方法:", style="cyan")
    table = Table(show_header=True, header_style="bold")
    table.add_column("方法", style="cyan")
    table.add_column("中文名")
    table.add_column("精度")
    table.add_column("说明")

    for m in list_relativistic_methods():
        table.add_row(m.name, m.name_cn, m.accuracy, m.notes or m.description[:40])
    console.print(table)


@list.command()
@click.option("--category", "-c", help="按类别筛选")
def basis(category):
    if category:
        results = list_basis_sets(category=category)
        console.print(f"\n类别 '{category}' 的基组:", style="bold")
    else:
        results = list_basis_sets()
        console.print("\n所有可用基组:", style="bold")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("名称", style="cyan")
    table.add_column("描述")
    table.add_column("等级", justify="right")
    table.add_column("类别")

    for bs in results:
        table.add_row(bs.name, bs.description, str(bs.level), bs.category)
    console.print(table)


@list.command()
def solvents():
    console.print("\n可用溶剂:", style="bold")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("名称", style="cyan")
    table.add_column("中文名")
    table.add_column("介电常数", justify="right")
    table.add_column("类别")

    for s in list_solvents():
        table.add_row(s.name, s.name_cn, f"{s.dielectric:.2f}", s.category)
    console.print(table)


@list.command()
def tags():
    console.print("\n可用标签:", style="bold")
    for tag in list_tags():
        console.print(f"  • {tag}")


@main.command()
@click.argument("mol_name")
def xyz(mol_name):
    try:
        mol = get_molecule(mol_name)
        xyz_block = get_xyz_block(mol)
        console.print(f"\n{mol.name_cn} ({mol.formula}) 的 XYZ 坐标:\n")
        console.print(Syntax(xyz_block, "xyz", theme="monokai"))
    except KeyError as e:
        console.print(str(e), style="red")


@main.command()
@click.argument("mol_name")
def info(mol_name):
    try:
        mol = get_molecule(mol_name)
        console.print(f"\n{mol.name_cn} ({mol.formula})", style="bold")

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("属性", style="cyan")
        table.add_column("值")

        table.add_row("英文名", mol.name)
        table.add_row("中文名", mol.name_cn)
        table.add_row("分子式", mol.formula)
        table.add_row("SMILES", mol.smiles)
        table.add_row("电子数", str(mol.electrons or "未知"))
        table.add_row("电荷", str(mol.charge))
        table.add_row("自旋", str(mol.spin))
        table.add_row("自旋多重度", str(mol.multiplicity))
        table.add_row("对称性", mol.symmetry)
        table.add_row("原子数", str(mol.atom_count))
        table.add_row("标签", ", ".join(mol.tags))

        console.print(table)

        console.print(f"\nXYZ 坐标:")
        console.print(Syntax(get_xyz_block(mol), "xyz", theme="monokai"))

    except KeyError as e:
        console.print(str(e), style="red")


@main.command()
@click.argument("filepath", type=str)
@click.option("--name", "-n", help="分子名称（默认使用文件名）")
@click.option("--charge", "-c", default=0, help="电荷")
@click.option("--spin", "-s", default=0, help="未配对电子数")
def import_mol(filepath, name, charge, spin):
    from .molecule_sources import load_xyz_file, register_molecule
    from .molecules import get_xyz_block

    mol = load_xyz_file(filepath)
    if not mol:
        console.print(f"[FAIL] 无法加载文件: {filepath}", style="red")
        return

    if name:
        mol.name = name.lower().replace(" ", "_")
        mol.name_cn = name
    if charge:
        mol.charge = charge
    if spin:
        mol.spin = spin

    register_molecule(mol)

    console.print(f"\n[OK] 成功导入分子:", style="green bold")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("属性", style="cyan")
    table.add_column("值")
    table.add_row("名称", mol.name)
    table.add_row("分子式", mol.formula)
    table.add_row("原子数", str(mol.atom_count))
    table.add_row("电子数", str(mol.electrons or "?"))
    table.add_row("电荷", str(mol.charge))
    table.add_row("自旋", str(mol.spin))
    console.print(table)

    console.print(f"\nXYZ 坐标:")
    console.print(Syntax(get_xyz_block(mol), "xyz", theme="monokai"))
    console.print(f"\n提示: 现在可以直接使用 '{mol.name}' 进行计算", style="dim")


@main.command()
@click.argument("name", nargs=-1, type=str)
def search(name):
    if not name:
        console.print("请输入分子名称", style="red")
        return

    query = " ".join(name)
    console.print(f"\n正在 PubChem 搜索 '{query}'...", style="bold")

    from .molecule_sources import search_pubchem, register_molecule
    from .molecules import get_xyz_block

    mol = search_pubchem(query)
    if not mol:
        console.print(f"[FAIL] 未在 PubChem 找到 '{query}'", style="red")
        console.print("提示: 请检查拼写，或尝试使用英文名/IUPAC 名", style="dim")
        return

    register_molecule(mol)

    console.print(f"\n[OK] 找到分子:", style="green bold")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("属性", style="cyan")
    table.add_column("值")
    table.add_row("名称", mol.name)
    table.add_row("IUPAC 名", mol.name_cn)
    table.add_row("分子式", mol.formula)
    table.add_row("SMILES", mol.smiles)
    table.add_row("原子数", str(mol.atom_count))
    table.add_row("电子数", str(mol.electrons or "?"))
    table.add_row("来源", ", ".join(mol.tags))
    console.print(table)

    console.print(f"\n3D 坐标:")
    console.print(Syntax(get_xyz_block(mol), "xyz", theme="monokai"))
    console.print(f"\n提示: 现在可以直接使用 '{mol.name}' 进行计算", style="dim")


@main.command()
def version():
    from . import __version__
    console.print(f"Frank v{__version__}", style="bold cyan")
    console.print("计算化学终端智能体")
    console.print("能生成、能执行、能诊断、能解读")


def interactive_mode():
    print_banner()
    console.print("提示: 输入计算需求开始，输入 'help' 查看帮助，输入 'quit' 退出")
    console.print("   在输入前加 'run ' 执行计算，不加则只生成代码")
    console.print("   用 'search <名称>' 搜索 PubChem，'import <文件>' 导入 XYZ\n")

    agent = FrankAgent()

    while True:
        try:
            text = Prompt.ask("[bold cyan]Frank[/bold cyan]")

            if not text.strip():
                continue

            if text.lower() in ["quit", "exit", "q"]:
                console.print("再见！", style="bold")
                break

            if text.lower() in ["help", "h", "帮助"]:
                console.print(agent.get_help())
                continue

            if text.lower() in ["clear", "cls"]:
                console.clear()
                print_banner()
                continue

            if text.lower().startswith("import "):
                filepath = text[7:].strip()
                from .molecule_sources import load_xyz_file, register_molecule
                from .molecules import get_xyz_block
                mol = load_xyz_file(filepath)
                if mol:
                    register_molecule(mol)
                    console.print(f"[OK] 已导入: {mol.name_cn} ({mol.formula}), {mol.atom_count} 个原子", style="green")
                else:
                    console.print(f"[FAIL] 无法加载: {filepath}", style="red")
                continue

            if text.lower().startswith("search "):
                query = text[7:].strip()
                console.print(f"正在搜索 '{query}'...", style="bold")
                from .molecule_sources import search_pubchem, register_molecule
                mol = search_pubchem(query)
                if mol:
                    register_molecule(mol)
                    console.print(f"[OK] 找到: {mol.name_cn} ({mol.formula}), SMILES: {mol.smiles}", style="green")
                    console.print(f"   原子数: {mol.atom_count}, 电子数: {mol.electrons}", style="dim")
                    console.print(f"   现在可以直接用 '{mol.name}' 计算", style="dim")
                else:
                    console.print(f"[FAIL] 未找到 '{query}'", style="red")
                continue

            if text.lower().startswith("run "):
                text = text[4:].strip()
                console.print(f"\n正在执行计算...", style="bold")
                result = agent.run(text)
                if result["code"]:
                    console.print("\n生成的代码:", style="bold")
                    script = result["script"]
                    syntax = Syntax(script[:2000] + "\n..." if len(script) > 2000 else script,
                                   "python", theme="monokai", line_numbers=True)
                    console.print(Panel(syntax, title=result["code"].title, border_style="green"))
                print_execution_result(result)
            else:
                result = agent.process_request(text)
                print_code_result(result)

        except KeyboardInterrupt:
            console.print("\n再见！", style="bold")
            break
        except Exception as e:
            console.print(f"[FAIL] 错误: {str(e)}", style="red")


if __name__ == "__main__":
    main()
