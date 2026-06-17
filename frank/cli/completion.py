"""
Readline tab-completion for the Frank interactive REPL.

Provides context-aware completion for molecule names, methods,
basis sets, commands, and workflow types.
"""


class FrankCompleter:
    """Readline completer for the Frank interactive prompt."""

    def __init__(self):
        self._molecules = None
        self._methods = None
        self._basis_sets = None
        self.commands = [
            "quit", "exit", "help", "clear", "session",
            "search ", "import ", "run ",
            "compare ", "converge ", "batch ",
        ]
        self.workflow_types = [
            "opt_freq", "method_comparison", "basis_convergence",
            "pes_scan", "solvation",
        ]

    @property
    def molecules(self) -> list[str]:
        if self._molecules is None:
            try:
                from .molecules.database import list_molecules
                self._molecules = [m.name for m in list_molecules()]
            except Exception:
                self._molecules = []
        return self._molecules

    @property
    def methods(self) -> list[str]:
        if self._methods is None:
            methods = []
            try:
                from .methods.dft import list_dft_functionals
                methods.extend(m.name for m in list_dft_functionals())
            except Exception:
                pass
            try:
                from .methods.post_hf import list_post_hf_methods
                methods.extend(m.name for m in list_post_hf_methods())
            except Exception:
                pass
            try:
                from .methods.excited import list_excited_methods
                methods.extend(m.name for m in list_excited_methods())
            except Exception:
                pass
            self._methods = sorted(set(methods))
        return self._methods

    @property
    def basis_sets(self) -> list[str]:
        if self._basis_sets is None:
            try:
                from .basis import list_basis_sets
                self._basis_sets = [b.name for b in list_basis_sets()]
            except Exception:
                self._basis_sets = []
        return self._basis_sets

    def _get_context(self, text: str) -> str:
        """Determine completion context from input text."""
        text_lower = text.lower().strip()

        if text_lower.startswith("run "):
            return "general"
        if text_lower.startswith("search "):
            return "search"
        if text_lower.startswith("import "):
            return "file"
        if text_lower.startswith("compare "):
            return "molecule"
        if text_lower.startswith("converge "):
            return "molecule"
        if text_lower.startswith("batch "):
            return "molecule"

        return "command"

    def complete(self, text: str, state: int) -> str | None:
        """Standard readline completer protocol.

        Args:
            text: The current word being completed.
            state: Index of the completion match (0-based).

        Returns:
            The next completion match, or None if no more matches.
        """
        buffer = self._get_line_buffer()

        # Determine what to complete
        if buffer.startswith("search "):
            candidates = self._complete_molecule(text)
        elif buffer.startswith("import "):
            candidates = self._complete_file(text)
        elif buffer.startswith("compare ") or buffer.startswith("converge ") or buffer.startswith("batch "):
            parts = buffer.split()
            if len(parts) <= 2:
                candidates = self._complete_molecule(text)
            elif "compare" in buffer and len(parts) <= 3:
                candidates = self._complete_method(text)
            elif "converge" in buffer and len(parts) <= 3:
                candidates = self._complete_basis(text)
            else:
                candidates = self._complete_general(text)
        elif buffer.startswith("run "):
            candidates = self._complete_general(text)
        else:
            candidates = self._complete_command(text)

        try:
            return candidates[state]
        except IndexError:
            return None

    def _get_line_buffer(self) -> str:
        """Get the current readline line buffer."""
        try:
            import readline
            return readline.get_line_buffer()
        except (ImportError, AttributeError):
            return ""

    def _complete_command(self, text: str) -> list[str]:
        """Complete built-in commands."""
        matches = [c for c in self.commands if c.startswith(text)]
        return matches

    def _complete_molecule(self, text: str) -> list[str]:
        """Complete molecule names."""
        if not text:
            return self.molecules[:50]
        return [m for m in self.molecules if m.startswith(text.lower())]

    def _complete_method(self, text: str) -> list[str]:
        """Complete method names."""
        if not text:
            return self.methods
        return [m for m in self.methods if m.lower().startswith(text.lower())]

    def _complete_basis(self, text: str) -> list[str]:
        """Complete basis set names."""
        if not text:
            return self.basis_sets
        return [b for b in self.basis_sets if b.lower().startswith(text.lower())]

    def _complete_file(self, text: str) -> list[str]:
        """Complete file paths."""
        import glob
        if not text:
            pattern = "*"
        else:
            pattern = text + "*"
        matches = glob.glob(pattern)
        return matches

    def _complete_general(self, text: str) -> list[str]:
        """General completion combining all categories."""
        candidates = []
        candidates.extend(self._complete_molecule(text))
        candidates.extend(self._complete_method(text))
        candidates.extend(self._complete_basis(text))
        candidates.extend([w for w in self.workflow_types if w.startswith(text)])
        return candidates
