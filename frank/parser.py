import re
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SCFResult:
    energy: Optional[float] = None
    energy_ev: Optional[float] = None
    converged: bool = False
    n_cycles: int = 0
    mo_energies: list[float] = field(default_factory=list)
    mo_occ: list[float] = field(default_factory=list)
    homo: Optional[float] = None
    lumo: Optional[float] = None
    gap: Optional[float] = None
    dipole: Optional[list[float]] = None
    dipole_magnitude: Optional[float] = None
    n_electrons: int = 0
    n_basis: int = 0
    scf_type: str = ""


@dataclass
class MP2Result:
    hf_energy: Optional[float] = None
    mp2_corr: Optional[float] = None
    mp2_total: Optional[float] = None
    converged: bool = False


@dataclass
class CCSDResult:
    hf_energy: Optional[float] = None
    ccsd_corr: Optional[float] = None
    ccsd_total: Optional[float] = None
    ccsd_t_correction: Optional[float] = None
    ccsd_t_total: Optional[float] = None
    converged: bool = False


@dataclass
class TDDFTResult:
    n_states: int = 0
    excitation_energies: list[float] = field(default_factory=list)
    wavelengths: list[float] = field(default_factory=list)
    oscillator_strengths: list[float] = field(default_factory=list)
    transition_characters: list[str] = field(default_factory=list)


@dataclass
class FrequencyResult:
    frequencies: list[float] = field(default_factory=list)
    n_imaginary: int = 0
    imaginary_freqs: list[float] = field(default_factory=list)
    zpe: Optional[float] = None
    thermal_corr: Optional[float] = None
    enthalpy: Optional[float] = None
    free_energy: Optional[float] = None
    is_minimum: bool = True


@dataclass
class GeomOptResult:
    initial_energy: Optional[float] = None
    final_energy: Optional[float] = None
    energy_change: Optional[float] = None
    n_steps: int = 0
    converged: bool = False
    final_geometry: list[tuple[str, list[float]]] = field(default_factory=list)


@dataclass
class CASSCFResult:
    energy: Optional[float] = None
    n_cas_orb: int = 0
    n_cas_elec: int = 0
    ci_coefficients: list[float] = field(default_factory=list)
    converged: bool = False


class PySCFOutputParser:
    HARTREE_TO_EV = 27.211386
    HARTREE_TO_KCAL = 627.509
    BOHR_TO_ANGSTROM = 0.529177

    def parse_scf(self, output: str) -> SCFResult:
        result = SCFResult()

        energy_patterns = [
            r"converged SCF energy\s*=\s*([-\d.]+)",
            r"SCF energy\s*=\s*([-\d.]+)",
            r"E\(.*?\)\s*=\s*([-\d.]+)",
            r"Total energy\s*=\s*([-\d.]+)",
        ]
        for pattern in energy_patterns:
            match = re.search(pattern, output)
            if match:
                result.energy = float(match.group(1))
                result.energy_ev = result.energy * self.HARTREE_TO_EV
                result.converged = True
                break

        cycle_match = re.search(r"cycle\s*=?\s*(\d+)", output, re.IGNORECASE)
        if cycle_match:
            result.n_cycles = int(cycle_match.group(1))

        occ_patterns = [
            r"mo_occ\s*=\s*\[([\d\s.]+)\]",
            r"Occupation.*?:\s*([\d\s.]+)",
        ]
        for pattern in occ_patterns:
            match = re.search(pattern, output)
            if match:
                try:
                    result.mo_occ = [float(x) for x in match.group(1).split()]
                except:
                    pass
                break

        homo_pattern = r"HOMO.*?=\s*([-\d.]+)\s*(?:eV|au|Hartree)"
        lumo_pattern = r"LUMO.*?=\s*([-\d.]+)\s*(?:eV|au|Hartree)"
        homo_match = re.search(homo_pattern, output, re.IGNORECASE)
        lumo_match = re.search(lumo_pattern, output, re.IGNORECASE)

        if homo_match:
            result.homo = float(homo_match.group(1))
        if lumo_match:
            result.lumo = float(lumo_match.group(1))
        if result.homo and result.lumo:
            result.gap = result.lumo - result.homo

        dipole_pattern = r"dipole.*?\(.*?\)\s*([\-\d.]+)\s+([\-\d.]+)\s+([\-\d.]+)"
        dipole_match = re.search(dipole_pattern, output, re.IGNORECASE)
        if dipole_match:
            result.dipole = [
                float(dipole_match.group(1)),
                float(dipole_match.group(2)),
                float(dipole_match.group(3)),
            ]
            result.dipole_magnitude = sum(d**2 for d in result.dipole) ** 0.5

        nbasis_pattern = r"(\d+)\s+basis\s+functions"
        nbasis_match = re.search(nbasis_pattern, output, re.IGNORECASE)
        if nbasis_match:
            result.n_basis = int(nbasis_match.group(1))

        return result

    def parse_mp2(self, output: str) -> MP2Result:
        result = MP2Result()

        hf_match = re.search(r"HF\s+energy\s*=\s*([-\d.]+)", output)
        if hf_match:
            result.hf_energy = float(hf_match.group(1))

        corr_patterns = [
            r"MP2\s+corr.*?energy\s*=\s*([-\d.]+)",
            r"MP2\s+correlation\s+energy\s*=\s*([-\d.]+)",
            r"E\(MP2\)\s*=\s*([-\d.]+)",
        ]
        for pattern in corr_patterns:
            match = re.search(pattern, output)
            if match:
                result.mp2_corr = float(match.group(1))
                break

        total_match = re.search(r"MP2\s+total\s+energy\s*=\s*([-\d.]+)", output)
        if total_match:
            result.mp2_total = float(total_match.group(1))
        elif result.hf_energy and result.mp2_corr:
            result.mp2_total = result.hf_energy + result.mp2_corr

        if result.mp2_total:
            result.converged = True

        return result

    def parse_ccsd(self, output: str) -> CCSDResult:
        result = CCSDResult()

        hf_match = re.search(r"HF\s+energy\s*=\s*([-\d.]+)", output)
        if hf_match:
            result.hf_energy = float(hf_match.group(1))

        ccsd_corr_match = re.search(r"CCSD\s+corr.*?energy\s*=\s*([-\d.]+)", output)
        if ccsd_corr_match:
            result.ccsd_corr = float(ccsd_corr_match.group(1))

        ccsd_total_match = re.search(r"CCSD\s+total\s+energy\s*=\s*([-\d.]+)", output)
        if ccsd_total_match:
            result.ccsd_total = float(ccsd_total_match.group(1))

        t_match = re.search(r"\(T\)\s*=\s*([-\d.]+)", output)
        if t_match:
            result.ccsd_t_correction = float(t_match.group(1))

        ccsdt_match = re.search(r"CCSD\(T\)\s+total\s+energy\s*=\s*([-\d.]+)", output)
        if ccsdt_match:
            result.ccsd_t_total = float(ccsdt_match.group(1))
        elif result.ccsd_total and result.ccsd_t_correction:
            result.ccsd_t_total = result.ccsd_total + result.ccsd_t_correction

        if result.ccsd_total:
            result.converged = True

        return result

    def parse_tddft(self, output: str) -> TDDFTResult:
        result = TDDFTResult()

        exc_pattern = r"Excited\s+State\s+\d+.*?([\d.]+)\s*eV.*?([\d.]+)\s*nm"
        for match in re.finditer(exc_pattern, output):
            result.excitation_energies.append(float(match.group(1)))
            result.wavelengths.append(float(match.group(2)))

        osc_pattern = r"f=\s*([\d.]+)"
        for match in re.finditer(osc_pattern, output):
            result.oscillator_strengths.append(float(match.group(1)))

        result.n_states = len(result.excitation_energies)

        return result

    def parse_frequency(self, output: str) -> FrequencyResult:
        result = FrequencyResult()

        freq_pattern = r"Frequency.*?:\s*([\d\.\-\s]+)"
        freq_match = re.search(freq_pattern, output)
        if freq_match:
            try:
                result.frequencies = [float(x) for x in freq_match.group(1).split()]
            except:
                pass

        imag_pattern = r"Imaginary\s+Frequency.*?:\s*([\d\.\-\s]+)"
        imag_match = re.search(imag_pattern, output, re.IGNORECASE)
        if imag_match:
            try:
                result.imaginary_freqs = [float(x) for x in imag_match.group(1).split()]
                result.n_imaginary = len(result.imaginary_freqs)
            except:
                pass

        if not result.imaginary_freqs:
            result.imaginary_freqs = [f for f in result.frequencies if f < 0]
            result.n_imaginary = len(result.imaginary_freqs)

        result.is_minimum = result.n_imaginary == 0

        zpe_match = re.search(r"Zero-point\s+energy\s*=\s*([\-\d.]+)", output, re.IGNORECASE)
        if zpe_match:
            result.zpe = float(zpe_match.group(1))

        thermal_match = re.search(r"Thermal\s+correction.*?=\s*([\-\d.]+)", output, re.IGNORECASE)
        if thermal_match:
            result.thermal_corr = float(thermal_match.group(1))

        enthalpy_match = re.search(r"Total\s+Enthalpy\s*=\s*([\-\d.]+)", output, re.IGNORECASE)
        if enthalpy_match:
            result.enthalpy = float(enthalpy_match.group(1))

        free_match = re.search(r"Total\s+Free\s+Energy\s*=\s*([\-\d.]+)", output, re.IGNORECASE)
        if free_match:
            result.free_energy = float(free_match.group(1))

        return result

    def parse_geometry_opt(self, output: str) -> GeomOptResult:
        result = GeomOptResult()

        init_match = re.search(r"Initial.*?energy\s*=\s*([\-\d.]+)", output, re.IGNORECASE)
        if init_match:
            result.initial_energy = float(init_match.group(1))

        final_match = re.search(r"Optimized.*?energy\s*=\s*([\-\d.]+)", output, re.IGNORECASE)
        if not final_match:
            final_match = re.search(r"converged.*?energy\s*=\s*([\-\d.]+)", output, re.IGNORECASE)
        if final_match:
            result.final_energy = float(final_match.group(1))

        step_pattern = r"Step\s+(\d+)"
        steps = re.findall(step_pattern, output)
        if steps:
            result.n_steps = max(int(s) for s in steps)

        result.converged = "converged" in output.lower() or "optimization completed" in output.lower()

        return result

    def parse_casscf(self, output: str) -> CASSCFResult:
        result = CASSCFResult()

        energy_match = re.search(r"CASSCF\s+energy\s*=\s*([-\d.]+)", output)
        if not energy_match:
            energy_match = re.search(r"converged.*?energy\s*=\s*([-\d.]+)", output)
        if energy_match:
            result.energy = float(energy_match.group(1))
            result.converged = True

        cas_match = re.search(r"(\d+)\s+active\s+orbitals.*?(\d+)\s+active\s+electrons", output, re.IGNORECASE)
        if cas_match:
            result.n_cas_orb = int(cas_match.group(1))
            result.n_cas_elec = int(cas_match.group(2))

        return result

    def parse_from_file(self, log_file: str) -> dict:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        results = {}

        scf = self.parse_scf(content)
        if scf.energy is not None:
            results["scf"] = scf

        mp2 = self.parse_mp2(content)
        if mp2.mp2_total is not None:
            results["mp2"] = mp2

        ccsd = self.parse_ccsd(content)
        if ccsd.ccsd_total is not None:
            results["ccsd"] = ccsd

        tddft = self.parse_tddft(content)
        if tddft.n_states > 0:
            results["tddft"] = tddft

        freq = self.parse_frequency(content)
        if freq.frequencies:
            results["frequency"] = freq

        geomopt = self.parse_geometry_opt(content)
        if geomopt.n_steps > 0:
            results["geomopt"] = geomopt

        casscf = self.parse_casscf(content)
        if casscf.energy is not None:
            results["casscf"] = casscf

        return results

    def parse_from_stdout(self, stdout: str) -> dict:
        results = {}

        for line in stdout.split("\n"):
            if "_FRANK_RESULT_JSON:" in line:
                json_str = line.split("_FRANK_RESULT_JSON:", 1)[1].strip()
                try:
                    results["json"] = json.loads(json_str)
                except:
                    pass
                break

        scf = self.parse_scf(stdout)
        if scf.energy is not None:
            results["scf"] = scf

        return results
