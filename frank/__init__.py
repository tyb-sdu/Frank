"""
Frank -- Computational Chemistry Terminal Agent

A terminal agent that generates executable computational chemistry code.
Supports PySCF and Psi4 backends, covering HF, DFT, MP2, CCSD(T), TDDFT, CASSCF, and more.
"""

__version__ = "0.1.0"
__author__ = "Frank Team"


def get_version_string() -> str:
    """Return the formatted version string."""
    return f"Frank v{__version__}"
