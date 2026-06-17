import os
import re
import json
import urllib.request
import urllib.parse
from typing import Optional

from .molecules import Molecule, MOLECULES

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
_USER_AGENT = "Frank/0.2 (Computational Chemistry Agent)"


def search_pubchem(name: str) -> Optional[Molecule]:
    encoded_name = urllib.parse.quote(name.strip())
    props_url = (
        f"{PUBCHEM_BASE}/compound/name/{encoded_name}"
        f"/property/MolecularFormula,CanonicalSMILES,IUPACName/JSON"
    )
    try:
        props_data = _fetch_json(props_url)
    except _PubChemNotFound:
        return None
    except Exception:
        return None

    props = props_data.get("PropertyTable", {}).get("Properties", [{}])[0]
    cid = props.get("CID")
    formula = props.get("MolecularFormula", "")
    smiles = props.get("CanonicalSMILES") or props.get("ConnectivitySMILES") or ""
    iupac_name = props.get("IUPACName", name)

    if not cid or not smiles:
        return None

    sdf_url = f"{PUBCHEM_BASE}/compound/cid/{cid}/record/SDF?record_type=3d"
    try:
        sdf_text = _fetch_text(sdf_url)
        atoms = _parse_sdf_atoms(sdf_text)
    except Exception:
        atoms = _smiles_to_atoms(smiles)

    if not atoms:
        return None

    atom_xyz_lines = []
    for symbol, x, y, z in atoms:
        atom_xyz_lines.append(f"{symbol}  {x:.6f}  {y:.6f}  {z:.6f}")
    atom_xyz = "\n".join(atom_xyz_lines)

    electrons = _count_electrons(atoms)
    mol_name = name.strip().lower().replace(" ", "_").replace("-", "_")

    return Molecule(
        name=mol_name,
        name_cn=iupac_name,
        formula=formula,
        smiles=smiles,
        atom_xyz=atom_xyz,
        charge=0,
        spin=0,
        electrons=electrons,
        tags=["pubchem", f"cid_{cid}"],
    )


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise _PubChemNotFound(f"PubChem 未找到该分子")
        raise


def _fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


class _PubChemNotFound(Exception):
    pass


def _parse_sdf_atoms(sdf_text: str) -> list[tuple[str, float, float, float]]:
    lines = sdf_text.split("\n")
    if len(lines) < 4:
        return []

    counts_line = lines[3].strip()
    parts = counts_line.split()
    if len(parts) < 2:
        return []

    try:
        n_atoms = int(parts[0])
    except ValueError:
        return []

    atoms = []
    for i in range(4, 4 + n_atoms):
        if i >= len(lines):
            break
        line = lines[i].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
            symbol = parts[3]
            symbol = symbol[0].upper() + symbol[1:].lower() if len(symbol) > 1 else symbol.upper()
            atoms.append((symbol, x, y, z))
        except (ValueError, IndexError):
            continue

    return atoms


def _smiles_to_atoms(smiles: str) -> list[tuple[str, float, float, float]]:
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return []

        mol = Chem.AddHs(mol)
        AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
        AllChem.MMFFOptimizeMolecule(mol)

        conf = mol.GetConformer()
        atoms = []
        for i, atom in enumerate(mol.GetAtoms()):
            pos = conf.GetAtomPosition(i)
            atoms.append((atom.GetSymbol(), pos.x, pos.y, pos.z))
        return atoms
    except Exception:
        return []


_ATOMIC_NUMBERS = {
    "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8,
    "F": 9, "Ne": 10, "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15,
    "S": 16, "Cl": 17, "Ar": 18, "K": 19, "Ca": 20, "Sc": 21, "Ti": 22,
    "V": 23, "Cr": 24, "Mn": 25, "Fe": 26, "Co": 27, "Ni": 28, "Cu": 29,
    "Zn": 30, "Ga": 31, "Ge": 32, "As": 33, "Se": 34, "Br": 35, "Kr": 36,
    "Rb": 37, "Sr": 38, "Ag": 47, "I": 53, "Ba": 56, "Au": 79, "Pb": 82,
}


def _count_electrons(atoms: list[tuple[str, float, float, float]]) -> int:
    total = 0
    for symbol, _, _, _ in atoms:
        z = _ATOMIC_NUMBERS.get(symbol, 6)
        total += z
    return total


def load_xyz_file(filepath: str) -> Optional[Molecule]:
    if not os.path.isfile(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None
    return xyz_string_to_molecule(content, name=os.path.splitext(os.path.basename(filepath))[0])


def xyz_string_to_molecule(
    xyz_string: str,
    name: Optional[str] = None,
    charge: int = 0,
    spin: int = 0,
) -> Optional[Molecule]:
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
            symbol = symbol[0].upper() + symbol[1:].lower() if len(symbol) > 1 else symbol.upper()
            atoms.append((symbol, x, y, z))
        except (ValueError, IndexError):
            continue

    if not atoms:
        return None

    atom_xyz_lines = [f"{s}  {x:.6f}  {y:.6f}  {z:.6f}" for s, x, y, z in atoms]
    atom_xyz = "\n".join(atom_xyz_lines)

    electrons = _count_electrons(atoms) - charge
    formula = _build_formula(atoms)

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


def _build_formula(atoms: list[tuple[str, float, float, float]]) -> str:
    from collections import Counter
    counts = Counter(symbol for symbol, _, _, _ in atoms)

    parts = []
    if "C" in counts:
        c = counts.pop("C")
        parts.append(f"C{c}" if c > 1 else "C")
    if "H" in counts:
        h = counts.pop("H")
        parts.append(f"H{h}" if h > 1 else "H")
    for symbol in sorted(counts.keys()):
        n = counts[symbol]
        parts.append(f"{symbol}{n}" if n > 1 else symbol)

    return "".join(parts)


def resolve_molecule(query: str) -> Optional[Molecule]:
    query = query.strip()
    if not query:
        return None

    mol = _try_smiles(query)
    if mol:
        return mol

    if _looks_like_file_path(query):
        mol = load_xyz_file(query)
        if mol:
            return mol

    mol = search_pubchem(query)
    if mol:
        return mol

    if _looks_like_smiles(query):
        mol = search_pubchem_by_smiles(query)
        if mol:
            return mol

    return None


def _try_smiles(text: str) -> Optional[Molecule]:
    if len(text) > 100 or len(text) < 2:
        return None

    if any("一" <= c <= "鿿" for c in text):
        return None

    smiles_chars = set("()=#@/\\[]+-")
    has_smiles_chars = any(c in smiles_chars for c in text)
    is_ring_smiles = (
        text[0].islower() and
        any(c.isdigit() for c in text) and
        text.replace(" ", "").isalnum()
    )

    if not has_smiles_chars and not is_ring_smiles:
        return None

    from .molecule_utils import smiles_to_molecule
    return smiles_to_molecule(text)


def _looks_like_file_path(query: str) -> bool:
    if os.sep in query or "/" in query:
        return True
    if query.lower().endswith(".xyz"):
        return True
    return False


def _looks_like_smiles(text: str) -> bool:
    if len(text) > 100 or len(text) < 2:
        return False
    if any("一" <= c <= "鿿" for c in text):
        return False
    smiles_chars = set("()=#@/\\[]+-")
    if any(c in smiles_chars for c in text):
        return True
    if text[0].islower() and any(c.isdigit() for c in text) and text.isalnum():
        return True
    return False


def search_pubchem_by_smiles(smiles: str) -> Optional[Molecule]:
    encoded = urllib.parse.quote(smiles.strip())
    cid_url = f"{PUBCHEM_BASE}/compound/smiles/{encoded}/cids/JSON"
    try:
        cid_data = _fetch_json(cid_url)
        cids = cid_data.get("IdentifierList", {}).get("CID", [])
        if not cids:
            return None
        cid = cids[0]
    except Exception:
        return None
    return _fetch_molecule_by_cid(cid, default_name=smiles[:20])


def _fetch_molecule_by_cid(cid: int, default_name: str = "") -> Optional[Molecule]:
    props_url = (
        f"{PUBCHEM_BASE}/compound/cid/{cid}"
        f"/property/MolecularFormula,CanonicalSMILES,IUPACName/JSON"
    )
    try:
        props_data = _fetch_json(props_url)
    except Exception:
        return None

    props = props_data.get("PropertyTable", {}).get("Properties", [{}])[0]
    formula = props.get("MolecularFormula", "")
    smiles = props.get("CanonicalSMILES") or props.get("ConnectivitySMILES") or ""
    iupac_name = props.get("IUPACName", default_name or f"cid_{cid}")

    sdf_url = f"{PUBCHEM_BASE}/compound/cid/{cid}/record/SDF?record_type=3d"
    try:
        sdf_text = _fetch_text(sdf_url)
        atoms = _parse_sdf_atoms(sdf_text)
    except Exception:
        atoms = _smiles_to_atoms(smiles)

    if not atoms:
        return None

    atom_xyz_lines = []
    for symbol, x, y, z in atoms:
        atom_xyz_lines.append(f"{symbol}  {x:.6f}  {y:.6f}  {z:.6f}")
    atom_xyz = "\n".join(atom_xyz_lines)

    electrons = _count_electrons(atoms)
    mol_name = iupac_name.strip().lower().replace(" ", "_").replace("-", "_")[:40]

    return Molecule(
        name=mol_name,
        name_cn=iupac_name,
        formula=formula,
        smiles=smiles,
        atom_xyz=atom_xyz,
        charge=0,
        spin=0,
        electrons=electrons,
        tags=["pubchem", f"cid_{cid}"],
    )


def register_molecule(mol: Molecule) -> None:
    from .molecules import _add
    _add(mol)
