"""
异步 CLI — 支持异步操作的命令行界面。

功能：
1. 异步执行计算（不阻塞 UI）
2. 实时输出进度
3. 并行工作流
4. 支持取消（Ctrl+C）
"""

import asyncio
import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.live import Live
from rich.text import Text
from rich.prompt import Prompt

from .async_agent import AsyncFrankAgent
from .async_executor import AsyncTask, TaskStatus, format_task_status, format_tasks_table
from .molecules import list_molecules, get_molecule, search_molecules, get_xyz_block
from .diagnostics import format_diagnostics


console = Console()


def print_banner():
    """打印欢迎横幅。"""
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
║          计算化学终端智能体 v0.3.0                             ║
║          异步执行 · 并行计算 · 实时进度                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="bold cyan")


def print_task_result(task: AsyncTask, interpretation: str = ""):
    """打印任务结果。"""
    if task.success:
        console.print(f"\n[OK] 计算成功 (耗时 {task.duration:.1f} 秒)", style="green")

        # 显示输出
        if task.stdout:
            lines = task.stdout.strip().split("\n")
            # 过滤掉内部标记
            output_lines = [l for l in lines if not l.startswith("_FRANK_")]
            if output_lines:
                console.print("\n计算输出:", style="dim")
                for line in output_lines[-20:]:
                    console.print(f"  {line}", style="dim")
    else:
        console.print(f"\n[FAIL] 计算失败", style="red")
        if task.error_type:
            console.print(f"   错误类型: {task.error_type}")
        if task.error_message:
            console.print(f"   错误信息: {task.error_message}")

    # 解读
    if interpretation:
        console.print(interpretation)


# ============================================================
#  CLI 命令
# ============================================================

@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Frank — 计算化学终端智能体（异步版）"""
    if ctx.invoked_subcommand is None:
        asyncio.run(interactive_mode())


@main.command()
@click.argument("query", nargs=-1, type=str)
@click.option("--no-interpret", is_flag=True, help="不解读结果")
@click.option("--timeout", "-t", default=600, help="超时时间（秒）")
def run(query, no_interpret, timeout):
    """异步执行计算"""
    if not query:
        console.print("请输入计算需求", style="red")
        return

    text = " ".join(query)

    async def _run():
        agent = AsyncFrankAgent(timeout=timeout)

        console.print(f"\n正在执行计算...", style="bold")

        result = await agent.run(text, interpret=not no_interpret)

        # 打印代码
        if result["code"]:
            console.print("\n生成的代码:", style="bold")
            script = result["script"]
            syntax = Syntax(script[:2000] + "\n..." if len(script) > 2000 else script,
                           "python", theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title=result["code"].title, border_style="green"))

        # 打印结果
        task = result.get("task")
        if task:
            print_task_result(task, result.get("interpretation", ""))

    asyncio.run(_run())


@main.command()
@click.argument("molecule")
@click.option("--methods", "-m", default="HF,B3LYP,MP2", help="方法列表（逗号分隔）")
@click.option("--basis", "-b", default="6-31g*", help="基组")
@click.option("--timeout", "-t", default=600, help="超时时间（秒）")
@click.option("--max-parallel", "-p", default=4, help="最大并行数")
def compare(molecule, methods, basis, timeout, max_parallel):
    """并行方法对比"""
    methods_list = methods.split(",")

    async def _compare():
        agent = AsyncFrankAgent(timeout=timeout, max_parallel=max_parallel)

        console.print(f"\n正在并行执行 {len(methods_list)} 个计算...", style="bold")

        result = await agent.run_method_comparison(molecule, methods_list, basis)

        console.print(result.summary)

    asyncio.run(_compare())


@main.command()
@click.argument("molecule")
@click.option("--method", "-m", default="B3LYP", help="计算方法")
@click.option("--basis-sets", "-b", default="6-31g*,cc-pvdz,cc-pvtz", help="基组列表（逗号分隔）")
@click.option("--timeout", "-t", default=600, help="超时时间（秒）")
@click.option("--max-parallel", "-p", default=4, help="最大并行数")
def converge(molecule, method, basis_sets, timeout, max_parallel):
    """并行基组收敛性测试"""
    basis_list = basis_sets.split(",")

    async def _converge():
        agent = AsyncFrankAgent(timeout=timeout, max_parallel=max_parallel)

        console.print(f"\n正在并行测试 {len(basis_list)} 个基组...", style="bold")

        result = await agent.run_basis_convergence(molecule, method, basis_list)

        console.print(result.summary)

    asyncio.run(_converge())


@main.command()
@click.argument("molecules", nargs=-1, type=str)
@click.option("--method", "-m", default="B3LYP", help="计算方法")
@click.option("--basis", "-b", default="6-31g*", help="基组")
@click.option("--timeout", "-t", default=600, help="超时时间（秒）")
@click.option("--max-parallel", "-p", default=4, help="最大并行数")
def batch(molecules, method, basis, timeout, max_parallel):
    """并行计算多个分子"""
    if not molecules:
        console.print("请指定分子名称", style="red")
        return

    async def _batch():
        agent = AsyncFrankAgent(timeout=timeout, max_parallel=max_parallel)

        console.print(f"\n正在并行计算 {len(molecules)} 个分子...", style="bold")

        result = await agent.run_multi_molecule(list(molecules), method, basis)

        console.print(result.summary)

    asyncio.run(_batch())


@main.command()
def tasks():
    """显示所有任务状态"""
    async def _tasks():
        agent = AsyncFrankAgent()
        all_tasks = agent.get_all_tasks()

        if not all_tasks:
            console.print("没有任务", style="dim")
        else:
            console.print(format_tasks_table(all_tasks))

    asyncio.run(_tasks())


# ============================================================
#  交互模式
# ============================================================

async def interactive_mode():
    """异步交互模式。"""
    print_banner()
    console.print("提示: 输入计算需求开始，输入 'help' 查看帮助，输入 'quit' 退出")
    console.print("   支持的前缀: 'run '(执行), 'compare '(并行对比), 'converge '(基组收敛)\n")

    agent = AsyncFrankAgent()

    while True:
        try:
            text = await asyncio.get_event_loop().run_in_executor(
                None, lambda: Prompt.ask("[bold cyan]Frank[/bold cyan]")
            )

            if not text.strip():
                continue

            # 特殊命令
            if text.lower() in ["quit", "exit", "q"]:
                await agent.cancel_all()
                console.print("再见！", style="bold")
                break

            if text.lower() in ["help", "h", "帮助"]:
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
                    console.print("没有任务", style="dim")
                continue

            # 并行方法对比
            if text.lower().startswith("compare "):
                parts = text[8:].strip().split()
                if len(parts) >= 2:
                    molecule = parts[0]
                    methods = parts[1].split(",")
                    basis = parts[2] if len(parts) > 2 else "6-31g*"

                    console.print(f"\n正在并行执行 {len(methods)} 个计算...", style="bold")
                    result = await agent.run_method_comparison(molecule, methods, basis)
                    console.print(result.summary)
                else:
                    console.print("用法: compare <分子> <方法1,方法2,...> [基组]", style="yellow")
                continue

            # 基组收敛测试
            if text.lower().startswith("converge "):
                parts = text[9:].strip().split()
                if len(parts) >= 2:
                    molecule = parts[0]
                    basis_sets = parts[1].split(",")
                    method = parts[2] if len(parts) > 2 else "B3LYP"

                    console.print(f"\n正在并行测试 {len(basis_sets)} 个基组...", style="bold")
                    result = await agent.run_basis_convergence(molecule, method, basis_sets)
                    console.print(result.summary)
                else:
                    console.print("用法: converge <分子> <基组1,基组2,...> [方法]", style="yellow")
                continue

            # 批量计算
            if text.lower().startswith("batch "):
                parts = text[6:].strip().split()
                if len(parts) >= 1:
                    molecules = parts[0].split(",")
                    method = parts[1] if len(parts) > 1 else "B3LYP"
                    basis = parts[2] if len(parts) > 2 else "6-31g*"

                    console.print(f"\n正在并行计算 {len(molecules)} 个分子...", style="bold")
                    result = await agent.run_multi_molecule(molecules, method, basis)
                    console.print(result.summary)
                else:
                    console.print("用法: batch <分子1,分子2,...> [方法] [基组]", style="yellow")
                continue

            # 普通计算
            if text.lower().startswith("run "):
                text = text[4:].strip()

            console.print(f"\n正在执行计算...", style="bold")

            # 带进度回调的执行
            def on_output(line):
                # 只显示关键输出
                if "converged" in line.lower() or "energy" in line.lower():
                    console.print(f"  {line}", style="dim")

            result = await agent.run_with_streaming(text, on_output=on_output)

            # 打印代码
            if result.get("code"):
                console.print("\n生成的代码:", style="bold")
                script = result["script"]
                syntax = Syntax(script[:1500] + "\n..." if len(script) > 1500 else script,
                               "python", theme="monokai", line_numbers=True)
                console.print(Panel(syntax, title=result["code"].title, border_style="green"))

            # 打印结果
            task = result.get("task")
            if task:
                # 获取解读
                parsed = result.get("parsed", {})
                interpretation = ""
                if parsed:
                    from .interpreter import ResultInterpreter
                    interpreter = ResultInterpreter()
                    if "scf" in parsed:
                        interpretation = interpreter.interpret_scf(
                            parsed["scf"],
                            method=result["intent"].method or "HF",
                            mol_name=get_molecule(result["intent"].molecule).name_cn,
                        )

                print_task_result(task, interpretation)

        except KeyboardInterrupt:
            await agent.cancel_all()
            console.print("\n已取消所有任务", style="yellow")
            continue
        except Exception as e:
            console.print(f"[FAIL] 错误: {str(e)}", style="red")


if __name__ == "__main__":
    main()
