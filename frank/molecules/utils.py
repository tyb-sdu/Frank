from typing import Optional
from .database import Molecule


def smiles_to_molecule(
    smiles: str,
    name: Optional[str] = None,
    charge: int = 0,
    spin: int = 0,
) -> Optional[Molecule]:
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        return None

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    mol = Chem.AddHs(mol)

    try:
        AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
        AllChem.MMFFOptimizeMolecule(mol)
    except Exception:
        try:
            AllChem.EmbedMolecule(mol)
            AllChem.UFFOptimizeMolecule(mol)
        except Exception:
            return None

    conf = mol.GetConformer()
    atoms = mol.GetAtoms()
    lines = []
    for i, atom in enumerate(atoms):
        pos = conf.GetAtomPosition(i)
        symbol = atom.GetSymbol()
        lines.append(f"{symbol}  {pos.x:.6f}  {pos.y:.6f}  {pos.z:.6f}")

    atom_xyz = "\n".join(lines)

    electrons = sum(atom.GetAtomicNum() for atom in atoms) - charge

    formula = Chem.rdMolDescriptors.CalcMolFormula(mol)

    if name is None:
        name = f"mol_{smiles[:10]}"

    return Molecule(
        name=name.lower().replace(" ", "_"),
        name_cn=name,
        formula=formula,
        smiles=smiles,
        atom_xyz=atom_xyz,
        charge=charge,
        spin=spin,
        electrons=electrons,
        tags=["custom", "from_smiles"],
    )


def parse_xyz_string(xyz_string: str) -> Optional[list[tuple[str, list[float]]]]:
    lines = xyz_string.strip().split("\n")

    if not lines:
        return None

    atoms = []
    start_idx = 0

    try:
        n_atoms = int(lines[0].strip())
        start_idx = 2 if len(lines) > 1 else 1
    except ValueError:
        start_idx = 0

    for i in range(start_idx, len(lines)):
        line = lines[i].strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 4:
            continue

        symbol = parts[0]
        try:
            x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
            atoms.append((symbol, [x, y, z]))
        except ValueError:
            continue

    return atoms if atoms else None


def xyz_to_molecule(
    xyz_string: str,
    name: Optional[str] = None,
    charge: int = 0,
    spin: int = 0,
) -> Optional[Molecule]:
    atoms = parse_xyz_string(xyz_string)
    if not atoms:
        return None

    lines = []
    for symbol, coords in atoms:
        lines.append(f"{symbol}  {coords[0]:.6f}  {coords[1]:.6f}  {coords[2]:.6f}")
    atom_xyz = "\n".join(lines)

    atomic_numbers = {
        "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8,
        "F": 9, "Ne": 10, "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15,
        "S": 16, "Cl": 17, "Ar": 18, "K": 19, "Ca": 20, "Fe": 26, "Cu": 29,
        "Zn": 30, "Br": 35, "I": 53,
    }

    electrons = 0
    for symbol, _ in atoms:
        z = atomic_numbers.get(symbol, 0)
        if z == 0:
            z = 6
        electrons += z
    electrons -= charge

    from collections import Counter
    atom_counts = Counter(symbol for symbol, _ in atoms)
    formula_parts = []
    for symbol in ["C", "H"]:
        if symbol in atom_counts:
            count = atom_counts.pop(symbol)
            formula_parts.append(f"{symbol}{count if count > 1 else ''}")
    for symbol in sorted(atom_counts.keys()):
        count = atom_counts[symbol]
        formula_parts.append(f"{symbol}{count if count > 1 else ''}")
    formula = "".join(formula_parts)

    if name is None:
        name = f"custom_{formula}"

    return Molecule(
        name=name.lower().replace(" ", "_"),
        name_cn=name,
        formula=formula,
        smiles="",
        atom_xyz=atom_xyz,
        charge=charge,
        spin=spin,
        electrons=electrons,
        tags=["custom", "from_xyz"],
    )


def validate_molecule(mol: Molecule) -> list[str]:
    issues = []

    atoms = mol.atom_xyz.strip().split("\n")
    if len(atoms) == 0:
        issues.append("分子没有原子坐标")

    for i, line in enumerate(atoms):
        parts = line.strip().split()
        if len(parts) < 4:
            issues.append(f"第 {i+1} 行坐标格式错误: {line}")
            continue

        symbol = parts[0]
        try:
            x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
        except ValueError:
            issues.append(f"第 {i+1} 行坐标不是有效数字: {line}")

    if mol.charge != 0 and mol.spin == 0:
        if mol.electrons and mol.electrons % 2 != 0:
            issues.append(f"带电分子 {mol.formula} 有奇数电子，可能需要设置 spin=1")

    return issues
