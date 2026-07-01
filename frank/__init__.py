"""
Frank -- Computational Chemistry Terminal Agent

A terminal agent that generates executable computational chemistry code.
Uses the PySCF backend, covering HF, DFT, MP2, CCSD(T), TDDFT, CASSCF, NEVPT2,
ADC(2), EOM-CCSD, and more.
"""

__version__ = "0.1.0"
__author__ = "Frank Team"


def get_version_string() -> str:
    """Return the formatted version string."""
    return f"Frank v{__version__}"
