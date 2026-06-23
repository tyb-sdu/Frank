"""Molecular structure validation — Aitomia-inspired plausibility checks."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from .database import Molecule


@dataclass
class ValidationResult:
    valid: bool = True
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.valid = False


_ATOMIC_MASSES_ORDER = ["C", "H", "O", "N", "S", "P", "F", "Cl", "Br", "I"]


def _parse_formula(formula: str) -> Counter[str]:
    """Parse molecular formula like C6H6O into element counts."""
    if not formula:
        return Counter()
    counts: Counter[str] = Counter()
    for match in re.finditer(r"([A-Z][a-z]?)(\d*)", formula):
        el, num = match.group(1), match.group(2)
        counts[el] += int(num) if num else 1
    return counts


def count_elements_from_xyz(mol: Molecule) -> Counter[str]:
    counts: Counter[str] = Counter()
    for line in mol.atom_xyz.strip().split("\n"):
        parts = line.split()
        if len(parts) >= 4:
            symbol = parts[0]
            symbol = symbol[0].upper() + symbol[1:].lower() if len(symbol) > 1 else symbol.upper()
            counts[symbol] += 1
    return counts


def validate_structure(mol: Molecule, expected_formula: Optional[str] = None) -> ValidationResult:
    """Validate a retrieved/generated 3D structure for chemical plausibility."""
    result = ValidationResult()
    xyz_counts = count_elements_from_xyz(mol)

    if not xyz_counts:
        result.add_error("Structure contains no atoms.")
        return result

    formula = expected_formula or mol.formula
    if formula:
        expected = _parse_formula(formula)
        if expected:
            total_expected = sum(expected.values())
            total_actual = sum(xyz_counts.values())
            if total_expected != total_actual:
                result.add_error(
                    f"Atom count mismatch: formula {formula} expects {total_expected} atoms, "
                    f"structure has {total_actual}."
                )
            for el, n in expected.items():
                actual = xyz_counts.get(el, 0)
                if actual != n:
                    result.add_warning(
                        f"Element {el}: formula expects {n}, structure has {actual}."
                    )

    # Graph-isomorphism check when SMILES is available (RDKit)
    if mol.smiles:
        graph_ok, graph_msg = _check_graph_consistency(mol)
        if not graph_ok:
            result.add_warning(graph_msg)
        stereo_ok, stereo_msg = _check_stereochemistry(mol)
        if not stereo_ok:
            result.add_warning(stereo_msg)

    return result


def _check_graph_consistency(mol: Molecule) -> tuple[bool, str]:
    """Compare molecular graph from SMILES vs XYZ via RDKit."""
    try:
        from rdkit import Chem
    except ImportError:
        return True, ""

    ref = Chem.MolFromSmiles(mol.smiles)
    if ref is None:
        return True, ""

    xyz_block = f"{mol.atom_count}\n{mol.name}\n{mol.atom_xyz.strip()}"
    xyz_mol = Chem.MolFromXYZBlock(xyz_block)
    if xyz_mol is None:
        return True, ""

    ref_no_h = Chem.RemoveHs(ref)
    xyz_no_h = Chem.RemoveHs(xyz_mol)

    if ref_no_h.GetNumAtoms() != xyz_no_h.GetNumAtoms():
        return False, (
            f"Heavy-atom count mismatch: SMILES has {ref_no_h.GetNumAtoms()}, "
            f"XYZ has {xyz_no_h.GetNumAtoms()}."
        )

    return True, ""


def _check_stereochemistry(mol: Molecule) -> tuple[bool, str]:
    """Verify stereochemical descriptors in SMILES are preserved in 3D geometry."""
    try:
        from rdkit import Chem
    except ImportError:
        return True, ""

    ref = Chem.MolFromSmiles(mol.smiles)
    if ref is None:
        return True, ""

    chiral_centers = Chem.FindMolChiralCenters(ref, includeUnassigned=False)
    if not chiral_centers:
        return True, ""

    xyz_block = f"{mol.atom_count}\n{mol.name}\n{mol.atom_xyz.strip()}"
    xyz_mol = Chem.MolFromXYZBlock(xyz_block)
    if xyz_mol is None:
        return True, ""

    try:
        Chem.AssignStereochemistryFrom3D(xyz_mol)
        xyz_centers = Chem.FindMolChiralCenters(xyz_mol, includeUnassigned=True)
        unassigned = [c for c in xyz_centers if c[1] == "?"]
        if unassigned:
            return False, (
                f"Stereochemistry ambiguous: {len(unassigned)} chiral center(s) "
                f"could not be assigned from 3D geometry."
            )
    except Exception:
        pass

    return True, ""


def resolve_smiles_via_cactus(name: str) -> Optional[str]:
    """Resolve molecule name to SMILES via NIH Cactus Chemical Identifier Resolver."""
    import urllib.error
    import urllib.parse
    import urllib.request

    encoded = urllib.parse.quote(name.strip())
    url = f"https://cactus.nci.nih.gov/chemical/structure/{encoded}/smiles"
    req = urllib.request.Request(url, headers={"User-Agent": "Frank/0.2"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            smiles = resp.read().decode("utf-8").strip()
            if smiles and "html" not in smiles.lower() and len(smiles) < 500:
                return smiles.split("\n")[0].strip()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        pass
    return None
