"""Deterministic reaction stoichiometry via atom-conservation null-space analysis.

Inspired by Aitomia: build an atom-conservation matrix from species compositions
and solve for stoichiometric coefficients mathematically (scipy.linalg.null_space),
so the LLM never performs unit or stoichiometry arithmetic.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.linalg import null_space

from ..molecules.database import Molecule, get_molecule


@dataclass
class StoichiometryResult:
    reactants: list[tuple[str, int]] = field(default_factory=list)
    products: list[tuple[str, int]] = field(default_factory=list)
    balanced: bool = False
    error: str = ""


def count_elements(mol: Molecule) -> Counter[str]:
    """Count elements from XYZ coordinates."""
    counts: Counter[str] = Counter()
    for line in mol.atom_xyz.strip().split("\n"):
        parts = line.split()
        if len(parts) >= 4:
            symbol = parts[0]
            symbol = symbol[0].upper() + symbol[1:].lower() if len(symbol) > 1 else symbol.upper()
            counts[symbol] += 1
    return counts


def _gcd_list(values: list[int]) -> int:
    from math import gcd
    result = abs(values[0])
    for v in values[1:]:
        result = gcd(result, abs(v))
    return result or 1


def _to_integer_coefficients(vec: np.ndarray, reactant_count: int) -> Optional[np.ndarray]:
    """Convert null-space vector to smallest positive integer coefficients."""
    if vec.size == 0:
        return None

    col = vec[:, 0] if vec.ndim == 2 else vec
    if np.allclose(col, 0):
        return None

    # Flip sign so reactant coefficients are positive
    reactant_part = col[:reactant_count]
    if np.any(reactant_part < 0):
        col = -col

    reactant_part = col[:reactant_count]
    if np.any(reactant_part <= 0):
        return None

    scaled = col / np.min(reactant_part[reactant_part > 0])
    rounded = np.round(scaled).astype(int)
    if np.allclose(scaled, rounded, atol=1e-6):
        g = _gcd_list(rounded.tolist())
        return (rounded // g).astype(int)

    # Fallback: scale by LCM of denominators from rational approximation
    from fractions import Fraction
    fracs = [Fraction(float(x)).limit_denominator(20) for x in scaled]
    denom_lcm = 1
    for f in fracs:
        denom_lcm = denom_lcm * f.denominator // _gcd_list([denom_lcm, f.denominator])
    ints = np.array([int(round(float(x) * denom_lcm)) for x in scaled], dtype=int)
    g = _gcd_list(ints.tolist())
    ints //= g
    if np.any(ints[:reactant_count] <= 0):
        return None
    return ints


def solve_stoichiometry(
    reactant_names: list[str],
    product_names: list[str],
) -> StoichiometryResult:
    """Determine mass-balanced stoichiometric coefficients from species compositions."""
    result = StoichiometryResult()
    all_names = reactant_names + product_names
    n_r = len(reactant_names)

    if n_r == 0 or len(product_names) == 0:
        result.error = "Need at least one reactant and one product."
        return result

    compositions: list[Counter[str]] = []
    for name in all_names:
        try:
            mol = get_molecule(name)
        except KeyError:
            result.error = f"Unknown species: {name}"
            return result
        comp = count_elements(mol)
        if not comp:
            result.error = f"No atoms found for species: {name}"
            return result
        compositions.append(comp)

    elements = sorted(set().union(*compositions))
    n_species = len(all_names)
    matrix = np.zeros((len(elements), n_species), dtype=float)

    for j, comp in enumerate(compositions):
        sign = 1.0 if j < n_r else -1.0
        for i, el in enumerate(elements):
            matrix[i, j] = sign * comp.get(el, 0)

    ns = null_space(matrix)
    if ns.size == 0:
        result.error = "Reaction is atomically imbalanced or underdetermined."
        return result

    coeffs = _to_integer_coefficients(ns, n_r)
    if coeffs is None:
        result.error = "Could not derive valid integer stoichiometric coefficients."
        return result

    result.reactants = [(reactant_names[i], int(coeffs[i])) for i in range(n_r)]
    result.products = [
        (product_names[i], int(coeffs[n_r + i])) for i in range(len(product_names))
    ]
    result.balanced = True
    return result


def format_energy_delta(delta_hartree: float) -> str:
    """Format relative energy in both Hartree and kcal/mol (Aitomia safeguard)."""
    delta_kcal = delta_hartree * 627.509
    return f"{delta_hartree:+.10f} Ha  ({delta_kcal:+.4f} kcal/mol)"
