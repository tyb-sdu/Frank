from dataclasses import dataclass, field
from typing import Optional
from abc import ABC, abstractmethod


@dataclass
class CodeBlock:
    section: str
    code: str
    order: int = 0
    description: str = ""


@dataclass
class GeneratedCode:
    title: str
    description: str
    blocks: list[CodeBlock] = field(default_factory=list)
    run_instructions: str = ""
    expected_output: str = ""

    def to_script(self, include_comments: bool = True) -> str:
        sections = {}
        for block in sorted(self.blocks, key=lambda b: b.order):
            if block.section not in sections:
                sections[block.section] = []
            sections[block.section].append(block)

        lines = []

        if include_comments:
            lines.append('"""')
            lines.append(f"  {self.title}")
            lines.append(f"  {self.description}")
            lines.append('"""')
            lines.append("")

        section_order = [
            "imports",
            "molecule",
            "method_setup",
            "calculation",
            "properties",
            "analysis",
            "visualization",
            "output",
        ]

        for section_name in section_order:
            if section_name in sections:
                if include_comments:
                    section_comments = {
                        "imports": "# ============================================================\n#  导入模块\n# ============================================================",
                        "molecule": "# ============================================================\n#  分子定义\n# ============================================================",
                        "method_setup": "# ============================================================\n#  方法设置\n# ============================================================",
                        "calculation": "# ============================================================\n#  计算\n# ============================================================",
                        "properties": "# ============================================================\n#  性质计算\n# ============================================================",
                        "analysis": "# ============================================================\n#  结果分析\n# ============================================================",
                        "visualization": "# ============================================================\n#  可视化\n# ============================================================",
                        "output": "# ============================================================\n#  输出结果\n# ============================================================",
                    }
                    if section_name in section_comments:
                        lines.append(section_comments[section_name])
                        lines.append("")

                for block in sections[section_name]:
                    if include_comments and block.description:
                        lines.append(f"# {block.description}")
                    lines.append(block.code)
                    lines.append("")

        return "\n".join(lines)


class TemplateEngine(ABC):

    @abstractmethod
    def generate_scf(self, mol_name: str, method: str, basis: str, **kwargs) -> GeneratedCode:
        pass

    @abstractmethod
    def generate_dft(self, mol_name: str, functional: str, basis: str, **kwargs) -> GeneratedCode:
        pass

    @abstractmethod
    def generate_mp2(self, mol_name: str, basis: str, **kwargs) -> GeneratedCode:
        pass

    @abstractmethod
    def generate_ccsd(self, mol_name: str, basis: str, **kwargs) -> GeneratedCode:
        pass

    @abstractmethod
    def generate_ccsd_t(self, mol_name: str, basis: str, **kwargs) -> GeneratedCode:
        pass

    @abstractmethod
    def generate_tddft(self, mol_name: str, functional: str, basis: str, n_states: int, **kwargs) -> GeneratedCode:
        pass

    @abstractmethod
    def generate_casscf(self, mol_name: str, basis: str, norb: int, nelec: int, **kwargs) -> GeneratedCode:
        pass

    @abstractmethod
    def generate_geometry_opt(self, mol_name: str, method: str, basis: str, **kwargs) -> GeneratedCode:
        pass

    @abstractmethod
    def generate_frequency(self, mol_name: str, method: str, basis: str, **kwargs) -> GeneratedCode:
        pass

    @abstractmethod
    def generate_nbo(self, mol_name: str, method: str, basis: str, **kwargs) -> GeneratedCode:
        pass
