from dataclasses import dataclass
from typing import Optional
from ..molecules.database import get_molecule, Molecule

@dataclass
class JobEstimation:
    estimated_time_str: str
    memory_req_str: str
    recommended_mode: str  # "local", "queue", or "export"
    reason: str

def estimate_job_cost(
    molecule_name: str,
    method: Optional[str] = None,
    basis: Optional[str] = None,
    calc_type: Optional[str] = None
) -> JobEstimation:
    """Evaluate whether a job should be run locally, queued, or exported to HPC."""
    try:
        mol = get_molecule(molecule_name)
    except KeyError:
        # Unknown molecule, default to export to be safe
        return JobEstimation("> 1h", "> 16GB", "export", "Unknown molecule size, recommend HPC.")

    atoms = mol.atom_count
    
    # Heavy methods
    is_post_hf = False
    if method:
        m_lower = method.lower()
        if any(x in m_lower for x in ["mp2", "ccsd", "casscf", "nevpt2", "caspt2"]):
            is_post_hf = True

    # Job type
    is_opt_freq = False
    if calc_type and calc_type.lower() in ["geometry", "frequency", "opt_freq", "pes_scan", "excited", "casscf"]:
        is_opt_freq = True

    # Rule based estimation
    if atoms <= 15 and not is_post_hf:
        return JobEstimation("< 2 min", "< 2GB", "local", "Small molecule with DFT/HF, suitable for local execution.")
    elif atoms <= 30 and not is_post_hf and not is_opt_freq:
        return JobEstimation("< 10 min", "< 4GB", "local", "Medium molecule single point, manageable locally.")
    elif atoms <= 30 and (is_post_hf or is_opt_freq):
        return JobEstimation("10 - 60 min", "4 - 8GB", "queue", "Medium molecule with heavy task, recommend queue or background execution.")
    else:
        return JobEstimation("> 1 hour", "> 8GB", "export", "Large molecule or heavy calculation, recommend exporting to HPC/Slurm.")

