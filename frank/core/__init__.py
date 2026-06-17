"""Core execution pipeline: executor, parser, diagnostics, interpreter, and recovery."""

from .executor import PySCFExecutor, ExecutionResult, save_execution_result
from .parser import PySCFOutputParser
from .diagnostics import DiagnosticsEngine, Diagnostic, format_diagnostics
from .interpreter import ResultInterpreter
from .visualizer import plot_result, plot_method_comparison, plot_basis_convergence, HAS_PLT
