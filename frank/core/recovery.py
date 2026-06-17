import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RecoveryAttempt:
    strategy: str
    description: str
    script_patch: str
    success: bool = False
    error_type: str = ""


@dataclass
class RecoveryResult:
    original_error: str
    attempts: list[RecoveryAttempt] = field(default_factory=list)
    final_success: bool = False
    retry_count: int = 0


SCF_RECOVERY_STRATEGIES = [
    RecoveryAttempt(
        strategy="scf_max_cycle",
        description="增加最大迭代次数 + 扩大 DIIS 空间",
        script_patch="mf.max_cycle = 200\nmf.diis_space = 8",
    ),
    RecoveryAttempt(
        strategy="scf_damp_shift",
        description="使用阻尼 + 能级移动",
        script_patch="mf.damp = 0.5\nmf.level_shift = 0.2",
    ),
    RecoveryAttempt(
        strategy="scf_newton",
        description="切换到二阶 Newton 方法",
        script_patch="mf = mf.newton()",
    ),
]

MEMORY_RECOVERY_STRATEGIES = [
    RecoveryAttempt(
        strategy="density_fit",
        description="使用密度拟合 (DF/RI) 加速",
        script_patch="mf = mf.density_fit()",
    ),
]

LINEAR_DEP_RECOVERY_STRATEGIES = [
    RecoveryAttempt(
        strategy="remove_diffuse",
        description="去掉弥散函数",
        script_patch="",
    ),
]

GEOMETRY_RECOVERY_STRATEGIES = [
    RecoveryAttempt(
        strategy="relax_convergence",
        description="放宽收敛标准",
        script_patch="mol.conv_tol = 1e-8\nmf.conv_tol = 1e-8",
    ),
]


def get_recovery_strategies(error_type: str) -> list[RecoveryAttempt]:
    strategies = {
        "scf_convergence": SCF_RECOVERY_STRATEGIES,
        "memory": MEMORY_RECOVERY_STRATEGIES,
        "linear_dep": LINEAR_DEP_RECOVERY_STRATEGIES,
        "geometry": GEOMETRY_RECOVERY_STRATEGIES,
    }
    return strategies.get(error_type, [])


def inject_recovery_code(script: str, patch: str) -> str:
    if not patch:
        return script

    lines = script.split("\n")
    inject_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("mf.kernel()") or stripped.startswith("cc.kernel()"):
            inject_idx = i
            break

    if inject_idx is None:
        lines.append("")
        lines.extend(patch.split("\n"))
        return "\n".join(lines)

    indent = ""
    for ch in lines[inject_idx]:
        if ch in (" ", "\t"):
            indent += ch
        else:
            break

    patch_lines = patch.split("\n")
    for j, pl in enumerate(patch_lines):
        lines.insert(inject_idx + j, indent + pl)

    return "\n".join(lines)


def patch_basis_remove_diffuse(basis: str) -> str:
    if basis.lower().startswith("aug-"):
        return basis[4:]
    result = basis.replace("+G", "G").replace("++G", "G")
    return result


def remove_assert_converged(script: str) -> str:
    lines = script.split("\n")
    filtered = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("assert") and "converged" in stripped:
            indent = ""
            for ch in line:
                if ch in (" ", "\t"):
                    indent += ch
                else:
                    break
            filtered.append(indent + "pass")
        else:
            filtered.append(line)
    return "\n".join(filtered)


def prepare_retry_script(
    original_script: str,
    error_type: str,
    attempt: RecoveryAttempt,
    original_basis: Optional[str] = None,
) -> str:
    script = original_script

    script = remove_assert_converged(script)

    if attempt.strategy == "remove_diffuse" and original_basis:
        new_basis = patch_basis_remove_diffuse(original_basis)
        script = script.replace(f"'{original_basis}'", f"'{new_basis}'")
        script = script.replace(f'"{original_basis}"', f'"{new_basis}"')
        return script

    script = inject_recovery_code(script, attempt.script_patch)

    return script
