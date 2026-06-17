import re
from typing import Optional

SCRIPT_HEADER = '''import json
import sys
import numpy as np
_FRANK_RESULTS = {}

'''

SCRIPT_FOOTER = '''

import json
import numpy as np

try:
    _results = {}

    try:
        _results["energy"] = float(mf.e_tot)
    except Exception:
        pass

    try:
        _results["converged"] = bool(mf.converged)
    except Exception:
        pass

    try:
        mo_e = mf.mo_energy
        mo_o = mf.mo_occ
        if isinstance(mo_e, np.ndarray) and mo_e.ndim == 2:
            _results["mo_energy_alpha"] = mo_e[0].tolist()
            _results["mo_energy_beta"] = mo_e[1].tolist()
            _results["mo_occ_alpha"] = mo_o[0].tolist()
            _results["mo_occ_beta"] = mo_o[1].tolist()
        else:
            _results["mo_energy"] = np.array(mo_e).tolist()
            _results["mo_occ"] = np.array(mo_o).tolist()
    except Exception:
        pass

    try:
        dip = mf.dip_moment()
        _results["dipole"] = np.array(dip).tolist()
    except Exception:
        pass

    try:
        grad = mf.Gradients().grad()
        _results["gradient"] = np.array(grad).tolist()
    except Exception:
        pass

    print("\\n_FRANK_RESULT_JSON:" + json.dumps(_results))

except Exception as e:
    print(f"\\n_FRANK_RESULT_ERROR: {str(e)}")
'''


def enhance_script(script: str) -> str:
    return SCRIPT_HEADER + script + SCRIPT_FOOTER


def classify_error(stderr: str, stdout: str) -> tuple[str, str, str]:
    """Classify a calculation error and return (error_type, message, plain_language).

    Returns:
        Tuple of (error_type, technical_message, plain_language_explanation).
    """
    combined = (stderr + stdout).lower()

    if "max cycle" in combined or "convergence" in combined or "scf not converged" in combined:
        return (
            "scf_convergence",
            "SCF did not converge. Suggestions: 1) increase max_cycle 2) use DIIS 3) try a different initial guess",
            "The self-consistent field calculation did not converge. "
            "This means the electron distribution could not be determined self-consistently. "
            "This is the most common issue in quantum chemistry calculations and often "
            "occurs for open-shell systems, transition metals, or poor initial geometries.",
        )

    if "memory" in combined or "oom" in combined or "killed" in combined:
        return (
            "memory",
            "Insufficient memory. Suggestions: 1) use a smaller basis set 2) enable density fitting (DF) 3) increase system memory",
            "The calculation exceeded available system memory. "
            "This is common for large molecules or large basis sets (memory scales as N^4 for DFT/HF "
            "and N^6 for CCSD). Consider using density fitting or a smaller basis set.",
        )

    if "basis" in combined and ("not found" in combined or "error" in combined):
        return (
            "basis_error",
            "Basis set definition error. Verify the basis set name spelling.",
            "The requested basis set was not recognized. "
            "Basis sets are mathematical descriptions of electron orbitals. "
            "Common choices: 6-31G*, cc-pVDZ, def2-SVP. Use 'frank list basis' to see available sets.",
        )

    if "integral" in combined or "eri" in combined:
        return (
            "integral_error",
            "Integral computation error. The molecular geometry may be problematic.",
            "An error occurred while computing electron repulsion integrals. "
            "This can happen when atoms are too close together or the basis set "
            "contains problematic functions for the current geometry.",
        )

    if "linear dependence" in combined or "lineardep" in combined:
        return (
            "linear_dep",
            "Basis set linear dependency. Suggestions: 1) remove diffuse functions 2) use an orthogonalizing basis",
            "Near-linear dependency detected in the basis set. "
            "This occurs when diffuse functions create nearly redundant descriptions of the same orbital space. "
            "Try removing diffuse functions (e.g., use 6-31G* instead of 6-31++G**).",
        )

    if "atom" in combined and ("too close" in combined or "overlap" in combined):
        return (
            "geometry",
            "Atoms too close together. Verify the molecular geometry.",
            "Two or more atoms are positioned too close together in the input geometry, "
            "causing a numerical overflow in the integral computation. "
            "Check the input coordinates for errors.",
        )

    if "traceback" in combined:
        lines = stderr.strip().split("\n")
        last_error = lines[-1] if lines else "Unknown Python error"
        return (
            "python_error",
            last_error,
            "An unexpected Python error occurred during the calculation. "
            "This may indicate a bug in the generated code or an issue with the PySCF installation.",
        )

    return (
        "unknown",
        stderr[:200] if stderr else "Unknown error",
        "An unrecognized error occurred. Review the standard output and error output for details.",
    )


def extract_results_from_stdout(stdout: str) -> dict:
    import json

    for line in reversed(stdout.split("\n")):
        if "_FRANK_RESULT_JSON:" in line:
            json_str = line.split("_FRANK_RESULT_JSON:", 1)[1].strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

    return {}


def extract_errors_from_stdout(stdout: str) -> Optional[str]:
    for line in reversed(stdout.split("\n")):
        if "_FRANK_RESULT_ERROR:" in line:
            return line.split("_FRANK_RESULT_ERROR:", 1)[1].strip()
    return None
