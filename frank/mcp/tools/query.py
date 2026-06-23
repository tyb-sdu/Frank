"""MCP query tools — molecules, methods, basis sets, solvents."""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from ...basis import list_basis_sets, recommend_basis_set, get_basis_set
from ...methods.dft import list_dft_functionals, list_dft_categories
from ...methods.post_hf import list_post_hf_methods
from ...methods.excited import list_excited_methods
from ...methods.relativistic import list_relativistic_methods
from ...methods.casscf import list_multiref_methods
from ...methods.solvation import list_solvents, list_solvation_models, get_solvent
from ...molecules.database import (
    get_molecule,
    list_molecules,
    list_tags,
    search_molecules,
    get_xyz_block,
)
from ...molecules.sources import search_pubchem, load_xyz_file, register_molecule
from ..serialization import molecule_summary


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def frank_list_molecules(
        tag: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 30,
    ) -> dict:
        """List built-in molecules in Frank's database.

        Args:
            tag: Filter by tag (e.g. 'aromatic', 'diatomic').
            search: Fuzzy search by name, formula, or Chinese name.
            limit: Maximum number of results (default 30).
        """
        if search:
            mols = search_molecules(search)
        else:
            mols = list_molecules(tag)
        seen = set()
        unique = []
        for mol in mols:
            if mol.name not in seen:
                seen.add(mol.name)
                unique.append(mol)
        return {
            "count": len(unique[:limit]),
            "molecules": [molecule_summary(m) for m in unique[:limit]],
            "tags": list_tags(),
        }

    @mcp.tool()
    def frank_get_molecule(name: str, include_xyz: bool = True) -> dict:
        """Get detailed information for a built-in molecule.

        Args:
            name: Molecule name, formula, or Chinese alias (e.g. 'h2o', '水').
            include_xyz: Include XYZ coordinate block in response.
        """
        mol = get_molecule(name)
        result = molecule_summary(mol)
        if include_xyz:
            result["xyz"] = get_xyz_block(mol)
        return result

    @mcp.tool()
    def frank_search_pubchem(name: str, register: bool = True) -> dict:
        """Search PubChem for a molecule and optionally register it in Frank.

        Args:
            name: Common or IUPAC name (e.g. 'caffeine', 'aspirin').
            register: If true, add the molecule to Frank's local database.
        """
        mol = search_pubchem(name)
        if mol is None:
            return {"found": False, "query": name, "message": "No PubChem match found."}
        if register:
            register_molecule(mol)
        return {"found": True, "molecule": molecule_summary(mol), "registered": register}

    @mcp.tool()
    def frank_import_molecule(
        filepath: str,
        name: Optional[str] = None,
        charge: int = 0,
        spin: int = 0,
    ) -> dict:
        """Import a molecule from an XYZ file into Frank's database.

        Args:
            filepath: Absolute or relative path to .xyz file.
            name: Optional custom name (defaults to filename stem).
            charge: Molecular charge.
            spin: Number of unpaired electrons.
        """
        mol = load_xyz_file(filepath)
        if mol is None:
            return {"success": False, "message": f"Failed to parse XYZ file: {filepath}"}
        if name:
            mol.name = name.lower().replace(" ", "_")
        mol.charge = charge
        mol.spin = spin
        register_molecule(mol)
        return {"success": True, "molecule": molecule_summary(mol)}

    @mcp.tool()
    def frank_list_methods() -> dict:
        """List all supported computational methods (SCF, DFT, post-HF, excited, multiref, relativistic)."""
        return {
            "dft_categories": list_dft_categories(),
            "dft_functionals": [
                {"name": f.name, "category": f.category, "description": f.description}
                for f in list_dft_functionals()
            ],
            "post_hf": [
                {"name": m.name, "description": m.description, "cost_scaling": m.cost_scaling}
                for m in list_post_hf_methods()
            ],
            "excited": [
                {"name": m.name, "description": m.description}
                for m in list_excited_methods()
            ],
            "multireference": [
                {"name": m.name, "description": m.description}
                for m in list_multiref_methods()
            ],
            "relativistic": [
                {"name": m.name, "description": m.description}
                for m in list_relativistic_methods()
            ],
        }

    @mcp.tool()
    def frank_list_basis_sets(category: Optional[str] = None) -> dict:
        """List available basis sets, optionally filtered by category.

        Categories: minimal, split-valence, polarized, correlation-consistent, ahlrichs, diffuse.
        """
        sets = list_basis_sets(category)
        return {
            "count": len(sets),
            "basis_sets": [
                {
                    "name": bs.name,
                    "description": bs.description,
                    "level": bs.level,
                    "category": bs.category,
                    "notes": bs.notes,
                }
                for bs in sets
            ],
        }

    @mcp.tool()
    def frank_recommend_basis(
        method: str,
        calc_type: str = "energy",
        accuracy: str = "medium",
        has_diffuse: bool = False,
    ) -> dict:
        """Recommend a basis set for a given method and calculation type.

        Args:
            method: Computational method (e.g. 'B3LYP', 'MP2', 'CCSD(T)').
            calc_type: Purpose — energy, geometry, frequency, excited, casscf.
            accuracy: low, medium, or high.
            has_diffuse: Whether diffuse functions are needed (anion/excited state).
        """
        recommended = recommend_basis_set(method, calc_type, accuracy, has_diffuse)
        try:
            info = get_basis_set(recommended)
            notes = info.notes
        except KeyError:
            notes = ""
        return {
            "recommended": recommended,
            "method": method,
            "calc_type": calc_type,
            "accuracy": accuracy,
            "notes": notes,
        }

    @mcp.tool()
    def frank_list_solvents(category: Optional[str] = None) -> dict:
        """List available solvents and solvation models (PCM, SMD, etc.)."""
        solvents = list_solvents(category)
        return {
            "solvation_models": [
                {"name": m.name, "description": m.description}
                for m in list_solvation_models()
            ],
            "solvents": [
                {
                    "name": s.name,
                    "name_cn": s.name_cn,
                    "category": s.category,
                    "dielectric": s.dielectric,
                    "pyscf_name": s.pyscf_name,
                }
                for s in solvents
            ],
        }

    @mcp.tool()
    def frank_get_solvent(name: str) -> dict:
        """Get details for a specific solvent (e.g. 'water', 'methanol')."""
        solvent = get_solvent(name)
        return {
            "name": solvent.name,
            "name_cn": solvent.name_cn,
            "category": solvent.category,
            "dielectric": solvent.dielectric,
            "pyscf_name": solvent.pyscf_name,
            "notes": solvent.notes,
        }
