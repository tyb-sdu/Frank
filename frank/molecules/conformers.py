"""Conformer search — RDKit ETKDG enumeration + MMFF94 ranking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .database import Molecule


@dataclass
class ConformerResult:
    molecule: Molecule
    conformer_id: int
    energy: float = 0.0
    label: str = ""


@dataclass
class ConformerSearchResult:
    query: str
    conformers: list[ConformerResult] = field(default_factory=list)
    smiles: str = ""
    error: str = ""

    @property
    def best(self) -> Optional[ConformerResult]:
        if not self.conformers:
            return None
        return min(self.conformers, key=lambda c: c.energy)


def generate_conformers(
    smiles: str,
    name: str,
    n_conformers: int = 10,
    charge: int = 0,
    spin: int = 0,
) -> ConformerSearchResult:
    """Generate and rank conformers from a SMILES string."""
    result = ConformerSearchResult(query=name, smiles=smiles)
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        result.error = "RDKit not available for conformer search."
        return result

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        result.error = f"Invalid SMILES: {smiles}"
        return result

    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    params.numThreads = 0
    cids = AllChem.EmbedMultipleConfs(mol, numConfs=n_conformers, params=params)
    if len(cids) == 0:
        result.error = "ETKDG failed to generate conformers."
        return result

    try:
        AllChem.MMFFOptimizeMoleculeConfs(mol, numThreads=0)
    except Exception:
        pass

    for cid in cids:
        conf = mol.GetConformer(cid)
        energy = 0.0
        try:
            props = AllChem.MMFFGetMoleculeProperties(mol)
            if props:
                ff = AllChem.MMFFGetMoleculeForceField(mol, props, confId=cid)
                if ff:
                    energy = ff.CalcEnergy()
        except Exception:
            pass

        atoms = []
        for atom in mol.GetAtoms():
            pos = conf.GetAtomPosition(atom.GetIdx())
            atoms.append((atom.GetSymbol(), pos.x, pos.y, pos.z))

        atom_xyz = "\n".join(f"{s}  {x:.6f}  {y:.6f}  {z:.6f}" for s, x, y, z in atoms)
        electrons = _count_electrons(atoms, charge)
        conf_name = f"{name}_conf{cid}"

        conf_mol = Molecule(
            name=conf_name,
            name_cn=f"{name} 构象 {cid}",
            formula=_build_formula(atoms),
            smiles=smiles,
            atom_xyz=atom_xyz,
            charge=charge,
            spin=spin,
            electrons=electrons,
            tags=["conformer", name],
        )
        result.conformers.append(ConformerResult(
            molecule=conf_mol,
            conformer_id=cid,
            energy=energy,
            label=f"conf_{cid}",
        ))

    result.conformers.sort(key=lambda c: c.energy)
    return result


def search_conformers_for_molecule(
    name: str,
    n_conformers: int = 10,
) -> ConformerSearchResult:
    """Search conformers for a named molecule (uses built-in or resolved SMILES)."""
    from .database import get_molecule
    from .sources import resolve_molecule, register_molecule

    try:
        mol = get_molecule(name)
    except KeyError:
        mol = resolve_molecule(name)
        if mol:
            register_molecule(mol)
        else:
            return ConformerSearchResult(query=name, error=f"Cannot resolve molecule: {name}")

    if not mol.smiles:
        return ConformerSearchResult(query=name, error=f"No SMILES for {name}")

    result = generate_conformers(mol.smiles, name, n_conformers, mol.charge, mol.spin)
    return result


def _count_electrons(atoms: list[tuple[str, float, float, float]], charge: int) -> int:
    from ..molecules.sources import _count_electrons as count_e
    return count_e(atoms) - charge


def _build_formula(atoms: list[tuple[str, float, float, float]]) -> str:
    from collections import Counter
    counts = Counter(s for s, _, _, _ in atoms)
    parts = []
    if "C" in counts:
        c = counts.pop("C")
        parts.append(f"C{c}" if c > 1 else "C")
    if "H" in counts:
        h = counts.pop("H")
        parts.append(f"H{h}" if h > 1 else "H")
    for sym in sorted(counts):
        n = counts[sym]
        parts.append(f"{sym}{n}" if n > 1 else sym)
    return "".join(parts)
