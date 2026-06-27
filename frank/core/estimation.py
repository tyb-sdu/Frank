"""Job feasibility estimation and execution-mode routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from ..methods.dft import get_dft_functional
from ..methods.post_hf import get_post_hf_method

if TYPE_CHECKING:
    from ..agent import ParsedIntent
    from ..molecules.database import Molecule


@dataclass
class JobEstimate:
    atom_count: int
    estimated_seconds: float
    estimated_memory_gb: float
    complexity_score: float
    recommended_mode: str
    reason: str
    warnings: list[str] = field(default_factory=list)


# Method cost tier (higher = more expensive)
_METHOD_TIER = {
    "HF": 1,
    "LDA": 1,
    "PBE": 1,
    "B3LYP": 2,
    "PBE0": 2,
    "M06-2X": 2,
    "wB97X-D": 2,
    "CAM-B3LYP": 2,
    "HSE06": 2,
    "MP2": 4,
    "SCS-MP2": 4,
    "CCSD": 5,
    "CCSD(T)": 6,
    "TDDFT": 3,
    "CASSCF": 5,
    "NEVPT2": 6,
    "CASPT2": 6,
}

_CALC_MULTIPLIER = {
    "energy": 1.0,
    "geometry": 8.0,
    "frequency": 12.0,
    "excited": 5.0,
    "casscf": 10.0,
    "nbo": 1.5,
    "solvation": 2.0,
}

_BASIS_MULTIPLIER = {
    "sto-3g": 0.5,
    "3-21g": 0.6,
    "6-31g*": 1.0,
    "6-31g**": 1.2,
    "6-31+g*": 1.3,
    "6-31++g**": 1.5,
    "6-311g**": 1.8,
    "cc-pvdz": 1.5,
    "cc-pvtz": 2.5,
    "cc-pvqz": 4.0,
    "aug-cc-pvdz": 2.0,
    "aug-cc-pvtz": 3.5,
    "def2-svp": 1.3,
    "def2-tzvp": 2.8,
}


def _method_tier(method: Optional[str]) -> int:
    if not method:
        return 2
    key = method.upper()
    if key in _METHOD_TIER:
        return _METHOD_TIER[key]
    try:
        get_dft_functional(method)
        return 2
    except KeyError:
        pass
    try:
        get_post_hf_method(method)
        return 4
    except KeyError:
        pass
    return 2


def _basis_multiplier(basis: Optional[str]) -> float:
    if not basis:
        return 1.0
    key = basis.lower()
    if key in _BASIS_MULTIPLIER:
        return _BASIS_MULTIPLIER[key]
    if "tzv" in key or "qzv" in key:
        return 3.0
    if "dz" in key or "svp" in key:
        return 1.5
    return 1.0


def estimate_job(
    intent: ParsedIntent,
    mol: Molecule,
    timeout: int = 600,
    local_atom_threshold: int = 30,
    export_atom_threshold: int = 50,
) -> JobEstimate:
    """Estimate computational cost and recommend an execution mode."""
    n_atoms = mol.atom_count
    method_tier = _method_tier(intent.method)
    calc_mult = _CALC_MULTIPLIER.get(intent.calc_type or "energy", 1.0)
    basis_mult = _basis_multiplier(intent.basis)

    # Rough wall-time model (seconds): scales with N^3 * method_tier * calc * basis
    base = max(n_atoms, 1) ** 3 * 0.002
    estimated_seconds = base * method_tier * calc_mult * basis_mult

    # Memory estimate (GB): ~0.05 GB per atom per tier for DFT-like methods
    estimated_memory_gb = max(0.5, n_atoms * 0.05 * method_tier * basis_mult)

    complexity = min(1.0, (estimated_seconds / max(timeout, 60)) * (method_tier / 4))

    warnings: list[str] = []
    recommended = "local"
    reason = "小分子、轻量方法，适合本机直接计算。"

    if n_atoms > export_atom_threshold:
        recommended = "export"
        reason = (
            f"体系较大（{n_atoms} 原子），本机计算易超时或内存不足，"
            "建议导出脚本后在集群/HPC 上运行。"
        )
    elif method_tier >= 5 and n_atoms > 12:
        recommended = "export"
        reason = (
            f"{intent.method or '后 HF 方法'} 对大体系（{n_atoms} 原子）成本很高，"
            "建议导出后在算力更强的机器上运行。"
        )
    elif estimated_seconds > timeout * 0.8:
        if n_atoms > local_atom_threshold:
            recommended = "export"
            reason = (
                f"预估耗时约 {estimated_seconds / 60:.0f} 分钟，超过本机 timeout（{timeout}s），"
                "建议导出脚本提交到队列或集群。"
            )
        else:
            recommended = "queue"
            reason = (
                f"预估耗时约 {estimated_seconds / 60:.0f} 分钟，接近 timeout 上限，"
                "建议使用异步队列（frank submit）或增大 timeout。"
            )
            warnings.append(f"预估计算时间 {estimated_seconds:.0f}s，默认 timeout 为 {timeout}s。")
    elif n_atoms > local_atom_threshold:
        recommended = "queue"
        reason = (
            f"原子数 {n_atoms} 超过本机推荐上限（{local_atom_threshold}），"
            "建议使用 frank submit 异步队列或 export 模式。"
        )
        warnings.append(f"体系含 {n_atoms} 个原子，本机直接计算可能较慢。")
    elif method_tier >= 4 and n_atoms > 20:
        recommended = "queue"
        reason = "中等规模体系 + 相关方法，建议使用队列异步执行。"
        warnings.append("MP2/CCSD 类方法在中等体系上耗时较长。")

    if intent.calc_type in ("geometry", "frequency") and n_atoms > 25 and recommended == "local":
        warnings.append("几何优化/频率计算在大体系上耗时显著增加。")

    return JobEstimate(
        atom_count=n_atoms,
        estimated_seconds=round(estimated_seconds, 1),
        estimated_memory_gb=round(estimated_memory_gb, 1),
        complexity_score=round(complexity, 2),
        recommended_mode=recommended,
        reason=reason,
        warnings=warnings,
    )


def resolve_execution_mode(
    user_mode: str,
    estimate: JobEstimate,
) -> str:
    """Resolve final execution mode from user preference and job estimate."""
    mode = (user_mode or "auto").lower()
    if mode == "auto":
        return estimate.recommended_mode
    if mode in ("local", "export", "queue"):
        return mode
    return estimate.recommended_mode
