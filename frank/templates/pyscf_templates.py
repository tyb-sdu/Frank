from typing import Optional
from .base import TemplateEngine, CodeBlock, GeneratedCode
from ..molecules.database import get_molecule, get_pyscf_geometry, Molecule
from ..basis import recommend_basis_set
from ..methods.dft import get_dft_functional, get_xc_string
from ..methods.post_hf import get_post_hf_method
from ..methods.excited import get_excited_method
from ..methods.solvation import get_solvent, get_solvation_model
from ..methods.scf import choose_scf_type


class PySCFTemplateEngine(TemplateEngine):

    def _get_mol(self, mol_name: str) -> Molecule:
        return get_molecule(mol_name)

    def _import_block(self, modules: list[str]) -> CodeBlock:
        imports = []
        for mod in modules:
            imports.append(f"from pyscf import {mod}")
        return CodeBlock(
            section="imports",
            code="\n".join(imports),
            order=0,
            description="Import required PySCF modules for the calculation",
        )

    def _molecule_block(self, mol: Molecule, unit: str = "Angstrom") -> CodeBlock:
        geometry = get_pyscf_geometry(mol)
        charge = mol.charge
        spin = mol.spin
        mult = mol.multiplicity

        code = f"""mol = gto.Mole()
mol.atom = '''
{geometry}
'''
mol.basis = BASIS
mol.charge = {charge}
mol.spin = {spin}  # 自旋多重度 = {mult}
mol.verbose = 4
mol.build()"""

        return CodeBlock(
            section="molecule",
            code=code,
            order=1,
            description=f"{mol.name_cn} ({mol.formula})",
        )

    def _scf_block(self, method: str = "RHF", mol: Optional[Molecule] = None) -> CodeBlock:
        if mol and mol.spin > 0:
            method = "UHF"

        code = f"""mf = scf.{method}(mol)
mf.kernel()
assert mf.converged, "SCF 未收敛！请检查分子几何或增加 max_cycle"
print(f"SCF 能量: {{mf.e_tot:.10f}} Hartree")"""

        return CodeBlock(
            section="calculation",
            code=code,
            order=10,
            description=f"Run {method} self-consistent field calculation to determine electronic ground state",
        )

    def _dft_block(self, functional: str, mol: Optional[Molecule] = None) -> CodeBlock:
        xc = get_xc_string(functional)
        scf_type = "UKS" if (mol and mol.spin > 0) else "RKS"

        code = f"""mf = dft.{scf_type}(mol)
mf.xc = '{xc}'
mf.kernel()
assert mf.converged, "DFT 未收敛！请检查分子几何或增加 max_cycle"
print(f"DFT ({functional}) 能量: {{mf.e_tot:.10f}} Hartree")"""

        return CodeBlock(
            section="calculation",
            code=code,
            order=10,
            description=f"Run density functional theory calculation using {functional} exchange-correlation functional",
        )

    def _mp2_block(self, mf_var: str = "mf") -> CodeBlock:
        code = f"""pt = mp.MP2({mf_var})
pt.kernel()
print(f"MP2 相关能: {{pt.e_corr:.10f}} Hartree")
print(f"MP2 总能量: {{pt.e_tot:.10f}} Hartree")"""

        return CodeBlock(
            section="calculation",
            code=code,
            order=10,
            description="Compute MP2 correlation energy correction to the Hartree-Fock reference",
        )

    def _ccsd_block(self, mf_var: str = "mf") -> CodeBlock:
        code = f"""mycc = cc.CCSD({mf_var})
mycc.kernel()
print(f"CCSD 相关能: {{mycc.e_corr:.10f}} Hartree")
print(f"CCSD 总能量: {{mycc.e_tot:.10f}} Hartree")"""

        return CodeBlock(
            section="calculation",
            code=code,
            order=10,
            description="CCSD 计算",
        )

    def _ccsd_t_block(self, mf_var: str = "mf") -> CodeBlock:
        code = f"""mycc = cc.CCSD({mf_var})
mycc.kernel()
et = mycc.ccsd_t()
print(f"CCSD 相关能: {{mycc.e_corr:.10f}} Hartree")
print(f"(T) 校正: {{et:.10f}} Hartree")
print(f"CCSD(T) 总能量: {{mycc.e_tot + et:.10f}} Hartree")"""

        return CodeBlock(
            section="calculation",
            code=code,
            order=10,
            description="CCSD(T) 计算",
        )

    def _tddft_block(self, functional: str, n_states: int, mol: Optional[Molecule] = None) -> CodeBlock:
        xc = get_xc_string(functional)
        scf_type = "UKS" if (mol and mol.spin > 0) else "RKS"

        code = f"""mf = dft.{scf_type}(mol)
mf.xc = '{xc}'
mf.kernel()

# TDDFT 激发态计算
td = mf.TDDFT()
td.nstates = {n_states}
td.kernel()
td.analyze()

# 打印激发能
print("\\n激发态能量 (eV):")
for i, e in enumerate(td.e):
    print(f"  状态 {{i+1}}: {{e*27.2114:.4f}} eV ({{1240.0/(e*27.2114):.1f}} nm)")"""

        return CodeBlock(
            section="calculation",
            code=code,
            order=10,
            description=f"TDDFT ({functional}) 激发态计算",
        )

    def _casscf_block(self, norb: int, nelec: int, mf_var: str = "mf") -> CodeBlock:
        code = f"""# CASSCF 计算
mc = mcscf.CASSCF({mf_var}, {norb}, {nelec})
mc.kernel()
print(f"CASSCF 能量: {{mc.e_tot:.10f}} Hartree")
print(f"CI 系数:")
print(mc.ci)"""

        return CodeBlock(
            section="calculation",
            code=code,
            order=10,
            description=f"CASSCF({norb},{nelec}) 计算",
        )

    def _nevpt2_block(self, mc_var: str = "mc") -> CodeBlock:
        code = f"""# NEVPT2 计算
pt = mrpt.NEVPT2({mc_var})
pt.kernel()
print(f"NEVPT2 能量: {{pt.e_tot:.10f}} Hartree")"""

        return CodeBlock(
            section="calculation",
            code=code,
            order=11,
            description="NEVPT2 校正",
        )

    def _casci_block(self, norb: int, nelec: int, mf_var: str = "mf") -> CodeBlock:
        code = f"""# CASCI 计算（不优化轨道）
mc = mcscf.CASCI({mf_var}, {norb}, {nelec})
mc.kernel()
print(f"CASCI 能量: {{mc.e_tot:.10f}} Hartree")"""

        return CodeBlock(
            section="calculation",
            code=code,
            order=10,
            description=f"CASCI({norb},{nelec}) 计算",
        )

    def _adc_block(self, n_states: int, mf_var: str = "mf") -> CodeBlock:
        code = f"""# ADC(2) 激发态计算
from pyscf import adc
myadc = adc.ADC({mf_var})
myadc.method = "adc(2)"
myadc.method_type = "ee"  # 电子激发 (EE)
myadc.kernel_gs()  # 基态相关能
e_ex = myadc.kernel(nroots={n_states})[0]

import numpy as np
print("\\nADC(2) 激发能 (eV):")
for i, e in enumerate(np.atleast_1d(e_ex)):
    ev = e * 27.2114
    print(f"  状态 {{i+1}}: {{ev:.4f}} eV ({{1240.0/ev:.1f}} nm)")"""

        return CodeBlock(
            section="calculation",
            code=code,
            order=10,
            description=f"ADC(2) 激发态计算（{n_states} 个态）",
        )

    def _eom_ccsd_block(self, n_states: int, mf_var: str = "mf") -> CodeBlock:
        code = f"""# EOM-CCSD 激发态计算
mycc = cc.CCSD({mf_var})
mycc.kernel()
print(f"CCSD 相关能: {{mycc.e_corr:.10f}} Hartree")

e_ee = mycc.eomee_ccsd_singlet(nroots={n_states})[0]

import numpy as np
print("\\nEOM-CCSD 单重激发能 (eV):")
for i, e in enumerate(np.atleast_1d(e_ee)):
    ev = e * 27.2114
    print(f"  状态 {{i+1}}: {{ev:.4f}} eV ({{1240.0/ev:.1f}} nm)")"""

        return CodeBlock(
            section="calculation",
            code=code,
            order=10,
            description=f"EOM-CCSD 激发态计算（{n_states} 个态）",
        )

    def _cisd_block(self, mf_var: str = "mf") -> CodeBlock:
        code = f"""# CISD 计算
myci = ci.CISD({mf_var})
myci.kernel()
print(f"CISD 相关能: {{myci.e_corr:.10f}} Hartree")
print(f"CISD 总能量: {{myci.e_tot:.10f}} Hartree")"""

        return CodeBlock(
            section="calculation",
            code=code,
            order=10,
            description="CISD 计算",
        )

    def _fci_block(self, mf_var: str = "mf") -> CodeBlock:
        code = f"""# FCI 全组态相互作用（仅适用于极小体系）
cisolver = fci.FCI({mf_var})
e_fci, ci_vec = cisolver.kernel()
print(f"FCI 总能量: {{e_fci:.10f}} Hartree")"""

        return CodeBlock(
            section="calculation",
            code=code,
            order=10,
            description="FCI 计算",
        )

    def _geometry_opt_block(self, mf_var: str = "mf") -> CodeBlock:
        code = f"""# 几何优化
from pyscf.geomopt.geometric_solver import optimize
mol_eq = optimize({mf_var}, maxsteps=100)
print(f"优化后能量: {{{mf_var}.e_tot:.10f}} Hartree")
print("优化后几何:")
print(mol_eq.atom_coords() * 0.529177)  # 转换为 Angstrom"""

        return CodeBlock(
            section="properties",
            code=code,
            order=20,
            description="Optimize molecular geometry to a stationary point on the potential energy surface",
        )

    def _frequency_block(self, mf_var: str = "mf") -> CodeBlock:
        code = f"""# 频率计算
from pyscf.hessian import thermo
hessian = {mf_var}.Hessian()
hessian.kernel()

# 热力学分析
freq_analysis = thermo.harmonic_analysis({mf_var}.mol, hessian)
print(f"振动频率 (cm^-1): {{freq_analysis['freq_energy']}}")
print(f"零点能: {{freq_analysis['ZPE'][0]:.6f}} Hartree")"""

        return CodeBlock(
            section="properties",
            code=code,
            order=21,
            description="Compute harmonic vibrational frequencies and thermochemical corrections",
        )

    def _population_analysis_block(self, mf_var: str = "mf") -> CodeBlock:
        code = f"""# 布居分析
pop, charges = {mf_var}.mulliken_pop()
print("Mulliken 原子电荷:")
for i, q in enumerate(charges):
    print(f"  原子 {{i}} ({{mol.atom_symbol(i)}}): {{q:+.4f}}")

# meta-Löwdin 布居（对基组更稳健）
try:
    pop_meta, charges_meta = {mf_var}.mulliken_meta()
    print("\\nmeta-Löwdin 原子电荷:")
    for i, q in enumerate(charges_meta):
        print(f"  原子 {{i}} ({{mol.atom_symbol(i)}}): {{q:+.4f}}")
except Exception as e:
    print(f"meta-Löwdin 布居不可用: {{e}}")"""

        return CodeBlock(
            section="analysis",
            code=code,
            order=30,
            description="Perform Mulliken and natural atomic orbital population analysis",
        )

    def _mo_analysis_block(self, mf_var: str = "mf") -> CodeBlock:
        code = f"""# 分子轨道分析（兼容 RHF/UHF）
import numpy as np
mo_energy = {mf_var}.mo_energy
mo_occ = {mf_var}.mo_occ

# 处理 UHF 的二维数组情况
if isinstance(mo_energy, (list, tuple)) and len(mo_energy) > 0 and isinstance(mo_energy[0], (list, np.ndarray)):
    # UHF: alpha 和 beta 分开
    mo_e_alpha = np.array(mo_energy[0])
    mo_e_beta = np.array(mo_energy[1]) if len(mo_energy) > 1 else mo_e_alpha
    homo_alpha = max(mo_e_alpha[mo_occ[0] > 0]) if any(mo_occ[0] > 0) else None
    lumo_alpha = min(mo_e_alpha[mo_occ[0] == 0]) if any(mo_occ[0] == 0) else None
    homo_beta = max(mo_e_beta[mo_occ[1] > 0]) if any(mo_occ[1] > 0) else None
    lumo_beta = min(mo_e_beta[mo_occ[1] == 0]) if any(mo_occ[1] == 0) else None
    print(f"Alpha 占据轨道数: {{int(sum(mo_occ[0]))}}")
    print(f"Beta 占据轨道数: {{int(sum(mo_occ[1]))}}")
    if homo_alpha is not None:
        print(f"Alpha HOMO: {{homo_alpha*27.2114:.4f}} eV")
    if lumo_alpha is not None:
        print(f"Alpha LUMO: {{lumo_alpha*27.2114:.4f}} eV")
    if homo_alpha is not None and lumo_alpha is not None:
        print(f"Alpha HOMO-LUMO 能隙: {{(lumo_alpha - homo_alpha)*27.2114:.4f}} eV")
else:
    # RHF/RKS
    mo_energy = np.array(mo_energy)
    mo_occ = np.array(mo_occ)
    n_occ = int(sum(mo_occ) / 2)
    print(f"占据轨道数: {{n_occ}}")
    print(f"HOMO 能量: {{mo_energy[n_occ-1]*27.2114:.4f}} eV")
    print(f"LUMO 能量: {{mo_energy[n_occ]*27.2114:.4f}} eV")
    print(f"HOMO-LUMO 能隙: {{(mo_energy[n_occ] - mo_energy[n_occ-1])*27.2114:.4f}} eV")"""

        return CodeBlock(
            section="analysis",
            code=code,
            order=31,
            description="Analyze molecular orbital energies, HOMO/LUMO levels, and frontier orbital gap",
        )

    def _dipole_block(self, mf_var: str = "mf") -> CodeBlock:
        code = f"""# 偶极矩
dip = {mf_var}.dip_moment()
print(f"偶极矩 (Debye): {{dip}}")"""

        return CodeBlock(
            section="properties",
            code=code,
            order=22,
            description="Compute electric dipole moment to assess molecular polarity",
        )

    def _solvation_block(self, model: str, solvent: str, mf_var: str = "mf") -> CodeBlock:
        solvent_info = get_solvent(solvent)
        eps = solvent_info.dielectric

        try:
            pyscf_method = get_solvation_model(model).pyscf_method.upper()
        except KeyError:
            pyscf_method = model.upper()

        if pyscf_method == "SMD":
            code = f"""# 溶剂化模型 (SMD, {solvent_info.name_cn})
from pyscf.solvent import smd
{mf_var}_sol = smd.SMD({mf_var})
{mf_var}_sol.with_solvent.solvent = '{solvent_info.pyscf_name}'  # SMD 内置溶剂参数
e_sol = {mf_var}_sol.kernel()
print(f"SMD 溶剂化总能量: {{e_sol:.10f}} Hartree")"""
            description = f"Apply SMD solvation model in {solvent_info.name_cn}"
        else:
            # PCM 家族：PCM(IEF-PCM)、CPCM(C-PCM)、COSMO 均由 solvent.PCM 提供
            pcm_method = {
                "PCM": "IEF-PCM",
                "CPCM": "C-PCM",
                "COSMO": "COSMO",
            }.get(pyscf_method, "IEF-PCM")
            code = f"""# 溶剂化模型 ({model}, {solvent_info.name_cn})
from pyscf import solvent
{mf_var}_sol = solvent.PCM({mf_var})
{mf_var}_sol.with_solvent.method = '{pcm_method}'
{mf_var}_sol.with_solvent.eps = {eps}  # {solvent_info.name_cn} 介电常数
e_sol = {mf_var}_sol.kernel()
print(f"{model} 溶剂化总能量: {{e_sol:.10f}} Hartree")"""
            description = (
                f"Apply {model} ({pcm_method}) implicit solvation model with "
                f"{solvent_info.name_cn} solvent (epsilon = {eps})"
            )

        return CodeBlock(
            section="method_setup",
            code=code,
            order=5,
            description=description,
        )

    def _output_setup(self, output_file: Optional[str]) -> tuple[CodeBlock, str]:
        if output_file:
            code = f"OUTPUT_FILE = '{output_file}'"
        else:
            code = "OUTPUT_FILE = None"

        return CodeBlock(
            section="imports",
            code=code,
            order=-1,
            description="Configure output file path for saving results",
        ), output_file

    def _basis_setup(self, basis: str) -> CodeBlock:
        code = f'BASIS = "{basis}"'
        return CodeBlock(
            section="imports",
            code=code,
            order=-1,
            description="Set basis set for the calculation",
        )

    def generate_scf(
        self,
        mol_name: str,
        method: str = "HF",
        basis: str = "6-31g*",
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        method = choose_scf_type(mol.spin)

        blocks = [
            self._import_block(["gto", "scf"]),
            self._basis_setup(basis),
            self._molecule_block(mol),
            self._scf_block(method, mol),
            self._mo_analysis_block("mf"),
            self._dipole_block("mf"),
        ]

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) {method} 计算",
            description=f"使用 {method}/{basis} 计算 {mol.name_cn} 的电子结构",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_{method.lower()}.py",
        )

    def generate_dft(
        self,
        mol_name: str,
        functional: str = "B3LYP",
        basis: str = "6-31g*",
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        func = get_dft_functional(functional)

        blocks = [
            self._import_block(["gto", "dft"]),
            self._basis_setup(basis),
            self._molecule_block(mol),
            self._dft_block(functional, mol),
            self._mo_analysis_block("mf"),
            self._dipole_block("mf"),
        ]

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) DFT ({functional}) 计算",
            description=f"使用 {functional}/{basis} 计算 {mol.name_cn} 的电子结构",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_dft.py",
        )

    def generate_mp2(
        self,
        mol_name: str,
        basis: str = "cc-pvdz",
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        method = choose_scf_type(mol.spin)

        blocks = [
            self._import_block(["gto", "scf", "mp"]),
            self._basis_setup(basis),
            self._molecule_block(mol),
            self._scf_block(method, mol),
            self._mp2_block(),
            self._mo_analysis_block("mf"),
        ]

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) MP2 计算",
            description=f"使用 MP2/{basis} 计算 {mol.name_cn} 的相关能",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_mp2.py",
        )

    def generate_ccsd(
        self,
        mol_name: str,
        basis: str = "cc-pvdz",
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        method = choose_scf_type(mol.spin)

        blocks = [
            self._import_block(["gto", "scf", "cc"]),
            self._basis_setup(basis),
            self._molecule_block(mol),
            self._scf_block(method, mol),
            self._ccsd_block(),
        ]

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) CCSD 计算",
            description=f"使用 CCSD/{basis} 计算 {mol.name_cn} 的相关能",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_ccsd.py",
        )

    def generate_ccsd_t(
        self,
        mol_name: str,
        basis: str = "cc-pvdz",
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        method = choose_scf_type(mol.spin)

        blocks = [
            self._import_block(["gto", "scf", "cc"]),
            self._basis_setup(basis),
            self._molecule_block(mol),
            self._scf_block(method, mol),
            self._ccsd_t_block(),
        ]

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) CCSD(T) 计算",
            description=f"使用 CCSD(T)/{basis} 计算 {mol.name_cn} 的相关能",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_ccsdt.py",
        )

    def generate_tddft(
        self,
        mol_name: str,
        functional: str = "B3LYP",
        basis: str = "6-31g*",
        n_states: int = 6,
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)

        blocks = [
            self._import_block(["gto", "dft"]),
            self._basis_setup(basis),
            self._molecule_block(mol),
            self._tddft_block(functional, n_states, mol),
        ]

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) TDDFT ({functional}) 激发态计算",
            description=f"使用 TDDFT({functional})/{basis} 计算 {mol.name_cn} 的 {n_states} 个激发态",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_tddft.py",
        )

    def generate_casscf(
        self,
        mol_name: str,
        basis: str = "cc-pvdz",
        norb: int = 4,
        nelec: int = 4,
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        method = choose_scf_type(mol.spin)

        blocks = [
            self._import_block(["gto", "scf", "mcscf"]),
            self._basis_setup(basis),
            self._molecule_block(mol),
            self._scf_block(method, mol),
            self._casscf_block(norb, nelec),
        ]

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) CASSCF({norb},{nelec}) 计算",
            description=f"使用 CASSCF({norb},{nelec})/{basis} 计算 {mol.name_cn}",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_casscf.py",
        )

    def generate_casci(
        self,
        mol_name: str,
        basis: str = "cc-pvdz",
        norb: int = 4,
        nelec: int = 4,
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        method = choose_scf_type(mol.spin)

        blocks = [
            self._import_block(["gto", "scf", "mcscf"]),
            self._basis_setup(basis),
            self._molecule_block(mol),
            self._scf_block(method, mol),
            self._casci_block(norb, nelec),
        ]

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) CASCI({norb},{nelec}) 计算",
            description=f"使用 CASCI({norb},{nelec})/{basis} 计算 {mol.name_cn}",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_casci.py",
        )

    def generate_nevpt2(
        self,
        mol_name: str,
        basis: str = "cc-pvdz",
        norb: int = 4,
        nelec: int = 4,
        output_file: Optional[str] = None,
        note: str = "",
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        method = choose_scf_type(mol.spin)

        blocks = [
            self._import_block(["gto", "scf", "mcscf", "mrpt"]),
            self._basis_setup(basis),
            self._molecule_block(mol),
            self._scf_block(method, mol),
            self._casscf_block(norb, nelec),
            self._nevpt2_block(),
        ]

        description = f"使用 CASSCF({norb},{nelec}) + NEVPT2/{basis} 计算 {mol.name_cn}"
        if note:
            description += f"（{note}）"

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) NEVPT2 计算",
            description=description,
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_nevpt2.py",
        )

    def generate_adc(
        self,
        mol_name: str,
        basis: str = "cc-pvdz",
        n_states: int = 6,
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        method = choose_scf_type(mol.spin)

        blocks = [
            self._import_block(["gto", "scf"]),
            self._basis_setup(basis),
            self._molecule_block(mol),
            self._scf_block(method, mol),
            self._adc_block(n_states),
        ]

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) ADC(2) 激发态计算",
            description=f"使用 ADC(2)/{basis} 计算 {mol.name_cn} 的 {n_states} 个激发态",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_adc2.py",
        )

    def generate_eom_ccsd(
        self,
        mol_name: str,
        basis: str = "cc-pvdz",
        n_states: int = 3,
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        method = choose_scf_type(mol.spin)

        blocks = [
            self._import_block(["gto", "scf", "cc"]),
            self._basis_setup(basis),
            self._molecule_block(mol),
            self._scf_block(method, mol),
            self._eom_ccsd_block(n_states),
        ]

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) EOM-CCSD 激发态计算",
            description=f"使用 EOM-CCSD/{basis} 计算 {mol.name_cn} 的 {n_states} 个激发态",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_eomccsd.py",
        )

    def generate_cisd(
        self,
        mol_name: str,
        basis: str = "cc-pvdz",
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        method = choose_scf_type(mol.spin)

        blocks = [
            self._import_block(["gto", "scf", "ci"]),
            self._basis_setup(basis),
            self._molecule_block(mol),
            self._scf_block(method, mol),
            self._cisd_block(),
        ]

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) CISD 计算",
            description=f"使用 CISD/{basis} 计算 {mol.name_cn} 的相关能",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_cisd.py",
        )

    def generate_fci(
        self,
        mol_name: str,
        basis: str = "cc-pvdz",
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        method = choose_scf_type(mol.spin)

        blocks = [
            self._import_block(["gto", "scf", "fci"]),
            self._basis_setup(basis),
            self._molecule_block(mol),
            self._scf_block(method, mol),
            self._fci_block(),
        ]

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) FCI 计算",
            description=f"使用 FCI/{basis} 计算 {mol.name_cn} 的精确能量（小体系）",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_fci.py",
        )

    def generate_geometry_opt(
        self,
        mol_name: str,
        method: str = "B3LYP",
        basis: str = "6-31g*",
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        is_dft = method.upper() not in ["HF", "RHF", "UHF", "ROHF"]

        if is_dft:
            blocks = [
                self._import_block(["gto", "dft"]),
                self._basis_setup(basis),
                self._molecule_block(mol),
                self._dft_block(method, mol),
                self._geometry_opt_block("mf"),
                self._frequency_block("mf"),
            ]
        else:
            scf_method = choose_scf_type(mol.spin)
            blocks = [
                self._import_block(["gto", "scf"]),
                self._basis_setup(basis),
                self._molecule_block(mol),
                self._scf_block(scf_method, mol),
                self._geometry_opt_block("mf"),
                self._frequency_block("mf"),
            ]

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) {method}/{basis} 几何优化",
            description=f"使用 {method}/{basis} 优化 {mol.name_cn} 的几何构型并计算频率",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_opt.py",
        )

    def generate_frequency(
        self,
        mol_name: str,
        method: str = "B3LYP",
        basis: str = "6-31g*",
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        is_dft = method.upper() not in ["HF", "RHF", "UHF", "ROHF"]

        if is_dft:
            blocks = [
                self._import_block(["gto", "dft"]),
                self._basis_setup(basis),
                self._molecule_block(mol),
                self._dft_block(method, mol),
                self._frequency_block("mf"),
            ]
        else:
            scf_method = choose_scf_type(mol.spin)
            blocks = [
                self._import_block(["gto", "scf"]),
                self._basis_setup(basis),
                self._molecule_block(mol),
                self._scf_block(scf_method, mol),
                self._frequency_block("mf"),
            ]

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) {method}/{basis} 频率计算",
            description=f"使用 {method}/{basis} 计算 {mol.name_cn} 的振动频率",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_freq.py",
        )

    def generate_nbo(
        self,
        mol_name: str,
        method: str = "B3LYP",
        basis: str = "6-31g*",
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        is_dft = method.upper() not in ["HF", "RHF", "UHF", "ROHF"]

        if is_dft:
            blocks = [
                self._import_block(["gto", "dft"]),
                self._basis_setup(basis),
                self._molecule_block(mol),
                self._dft_block(method, mol),
                self._population_analysis_block("mf"),
                self._mo_analysis_block("mf"),
            ]
        else:
            scf_method = choose_scf_type(mol.spin)
            blocks = [
                self._import_block(["gto", "scf"]),
                self._basis_setup(basis),
                self._molecule_block(mol),
                self._scf_block(scf_method, mol),
                self._population_analysis_block("mf"),
                self._mo_analysis_block("mf"),
            ]

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) {method}/{basis} NBO 分析",
            description=f"使用 {method}/{basis} 对 {mol.name_cn} 进行 NBO 布居分析",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_nbo.py",
        )

    def generate_solvation(
        self,
        mol_name: str,
        method: str = "B3LYP",
        basis: str = "6-31g*",
        solvent: str = "water",
        model: str = "PCM",
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        is_dft = method.upper() not in ["HF", "RHF", "UHF", "ROHF"]

        if is_dft:
            blocks = [
                self._import_block(["gto", "dft", "solvent"]),
                self._basis_setup(basis),
                self._molecule_block(mol),
                self._dft_block(method, mol),
                self._solvation_block(model, solvent),
            ]
        else:
            scf_method = choose_scf_type(mol.spin)
            blocks = [
                self._import_block(["gto", "scf", "solvent"]),
                self._basis_setup(basis),
                self._molecule_block(mol),
                self._scf_block(scf_method, mol),
                self._solvation_block(model, solvent),
            ]

        solvent_info = get_solvent(solvent)
        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) {method}/{basis} 溶剂化计算 ({solvent_info.name_cn})",
            description=f"使用 {method}/{basis} + {model} 计算 {mol.name_cn} 在 {solvent_info.name_cn} 中的溶剂化",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_solv.py",
        )

    def _relativistic_block(self, method: str = "DKH2", order: int = 2) -> CodeBlock:
        method_upper = method.upper()

        if method_upper in ["DKH", "DKH0", "DKH1", "DKH2"]:
            dkh_order = order if method_upper == "DKH" else int(method_upper[-1])
            code = f"""# 相对论效应: Douglas-Kroll-Hess (DKH{dkh_order})
mol.build(method='DKH{dkh_order}')
print(f"使用 DKH{dkh_order} 相对论方法")"""
        elif method_upper in ["X2C", "X2C1E"]:
            code = """# 相对论效应: 精确二分量 (X2C)
mol.build(method='X2C')
print("使用 X2C 精确二分量方法")"""
        else:
            code = f"""# 相对论效应: {method}
mol.build(method='{method_upper}')
print(f"使用 {method} 相对论方法")"""

        return CodeBlock(
            section="method_setup",
            code=code,
            order=5,
            description=f"相对论效应 ({method})",
        )

    def generate_relativistic(
        self,
        mol_name: str,
        method: str = "B3LYP",
        basis: str = "cc-pvdz",
        relativistic: str = "DKH2",
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        from ..methods.relativistic import get_relativistic_method

        mol = self._get_mol(mol_name)
        rel = get_relativistic_method(relativistic)
        is_dft = method.upper() not in ["HF", "RHF", "UHF", "ROHF"]

        blocks = [
            self._import_block(["gto", "dft" if is_dft else "scf"]),
            self._basis_setup(basis),
            self._molecule_block(mol),
            self._relativistic_block(relativistic, rel.order),
        ]

        if is_dft:
            blocks.append(self._dft_block(method, mol))
        else:
            scf_method = choose_scf_type(mol.spin)
            blocks.append(self._scf_block(scf_method, mol))

        blocks.append(self._mo_analysis_block("mf"))

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) {method}/{basis} + {relativistic}",
            description=f"使用 {method}/{basis} + {relativistic} 计算 {mol.name_cn}",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_rel.py",
        )

    def _density_fit_block(self, mf_var: str = "mf", aux_basis: str = None) -> CodeBlock:
        if aux_basis:
            code = f"""# 密度拟合 (DF/RI) 加速
{mf_var} = {mf_var}.density_fit(auxbasis='{aux_basis}')
print(f"使用密度拟合 (DF/RI)，辅助基组: {aux_basis}")"""
        else:
            code = f"""# 密度拟合 (DF/RI) 加速
{mf_var} = {mf_var}.density_fit()
print("使用密度拟合 (DF/RI) 加速计算")"""

        return CodeBlock(
            section="method_setup",
            code=code,
            order=6,
            description="密度拟合加速",
        )

    def generate_df_calculation(
        self,
        mol_name: str,
        method: str = "B3LYP",
        basis: str = "cc-pvdz",
        aux_basis: str = None,
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        is_dft = method.upper() not in ["HF", "RHF", "UHF", "ROHF"]

        blocks = [
            self._import_block(["gto", "dft" if is_dft else "scf", "df"]),
            self._basis_setup(basis),
            self._molecule_block(mol),
        ]

        if is_dft:
            blocks.append(self._dft_block(method, mol))
        else:
            scf_method = choose_scf_type(mol.spin)
            blocks.append(self._scf_block(scf_method, mol))

        blocks.append(self._density_fit_block("mf", aux_basis))
        blocks.append(self._mo_analysis_block("mf"))

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) {method}/{basis} + DF",
            description=f"使用密度拟合加速 {method}/{basis} 计算 {mol.name_cn}",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_df.py",
        )

    def _stability_analysis_block(self, mf_var: str = "mf") -> CodeBlock:
        code = f"""# 波函数稳定性分析
print("\\n=== 波函数稳定性分析 ===")

# 检查内部稳定性
try:
    mo_init = {mf_var}.mo_coeff
    stable = {mf_var}.stability()
    print(f"稳定性检查完成")

    # 如果不稳定，尝试重新优化
    if not stable:
        print("[WARN] 波函数不稳定，尝试重新优化...")
        {mf_var}.run()
        stable = {mf_var}.stability()
        if stable:
            print("[OK] 重新优化后波函数稳定")
        else:
            print("[FAIL] 波函数仍不稳定")
    else:
        print("[OK] 波函数稳定")
except Exception as e:
    print(f"稳定性分析出错: {{e}}")"""

        return CodeBlock(
            section="analysis",
            code=code,
            order=35,
            description="波函数稳定性分析",
        )

    def generate_stability_analysis(
        self,
        mol_name: str,
        method: str = "B3LYP",
        basis: str = "6-31g*",
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)
        is_dft = method.upper() not in ["HF", "RHF", "UHF", "ROHF"]

        blocks = [
            self._import_block(["gto", "dft" if is_dft else "scf"]),
            self._basis_setup(basis),
            self._molecule_block(mol),
        ]

        if is_dft:
            blocks.append(self._dft_block(method, mol))
        else:
            scf_method = choose_scf_type(mol.spin)
            blocks.append(self._scf_block(scf_method, mol))

        blocks.append(self._stability_analysis_block("mf"))
        blocks.append(self._mo_analysis_block("mf"))

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) 波函数稳定性分析",
            description=f"使用 {method}/{basis} 进行波函数稳定性分析",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_stab.py",
        )

    def _excited_state_opt_block(self, functional: str, n_states: int, state: int = 1) -> CodeBlock:
        code = f"""# 激发态几何优化 (TDDFT)
from pyscf import tddft

# TDDFT 计算
td = mf.TDDFT()
td.nstates = {n_states}
td.kernel()

# 选择优化的激发态（默认 S1）
target_state = {state}  # S1, S2, ... 对应 1, 2, ...

print(f"\\n优化激发态 S{{target_state}} 的几何...")

# 激发态梯度
g_td = td.nuc_grad_method()
g_td.state = target_state

# 激发态几何优化
from pyscf.geomopt.geometric_solver import optimize
mol_eq = optimize(g_td, maxsteps=100)

print(f"\\n激发态 S{{target_state}} 优化完成")
print(f"优化后能量: {{g_td.e_tot():.10f}} Hartree")"""

        return CodeBlock(
            section="calculation",
            code=code,
            order=10,
            description=f"激发态 S{state} 几何优化",
        )

    def generate_excited_state_opt(
        self,
        mol_name: str,
        functional: str = "B3LYP",
        basis: str = "6-31g*",
        n_states: int = 6,
        state: int = 1,
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        mol = self._get_mol(mol_name)

        blocks = [
            self._import_block(["gto", "dft"]),
            self._basis_setup(basis),
            self._molecule_block(mol),
            self._dft_block(functional, mol),
            self._excited_state_opt_block(functional, n_states, state),
        ]

        return GeneratedCode(
            title=f"{mol.name_cn} ({mol.formula}) 激发态 S{state} 几何优化",
            description=f"使用 TDDFT({functional})/{basis} 优化 {mol.name_cn} 的 S{state} 态几何",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python {mol_name}_es_opt.py",
        )

    def _pbc_molecule_block(self, lattice: str, a: float, basis: str) -> CodeBlock:
        code = f"""# 周期性体系定义
from pyscf import pbc
from pyscf.pbc import gto as pbc_gto
from pyscf.pbc import dft as pbc_dft

cell = pbc_gto.Cell()
cell.atom = '''
{self._get_lattice_atoms(lattice, a)}
'''
cell.a = '''
{a:.6f}  0.000000  0.000000
0.000000  {a:.6f}  0.000000
0.000000  0.000000  {a:.6f}
'''
cell.basis = '{basis}'
cell.verbose = 4
cell.build()"""

        return CodeBlock(
            section="molecule",
            code=code,
            order=1,
            description=f"周期性体系 ({lattice})",
        )

    def _get_lattice_atoms(self, lattice: str, a: float) -> str:
        lattices = {
            "diamond": f"""C  0.000000  0.000000  0.000000
C  {a/4:.6f}  {a/4:.6f}  {a/4:.6f}""",
            "fcc": f"""Cu  0.000000  0.000000  0.000000
Cu  {a/2:.6f}  {a/2:.6f}  0.000000
Cu  {a/2:.6f}  0.000000  {a/2:.6f}
Cu  0.000000  {a/2:.6f}  {a/2:.6f}""",
            "bcc": f"""Fe  0.000000  0.000000  0.000000
Fe  {a/2:.6f}  {a/2:.6f}  {a/2:.6f}""",
            "nacl": f"""Na  0.000000  0.000000  0.000000
Cl  {a/2:.6f}  0.000000  0.000000
Na  {a/2:.6f}  {a/2:.6f}  0.000000
Cl  0.000000  {a/2:.6f}  0.000000
Na  0.000000  0.000000  {a/2:.6f}
Cl  {a/2:.6f}  0.000000  {a/2:.6f}
Na  {a/2:.6f}  {a/2:.6f}  {a/2:.6f}
Cl  0.000000  {a/2:.6f}  {a/2:.6f}""",
        }
        return lattices.get(lattice, lattices["diamond"])

    def _pbc_scf_block(self, kpts: list = None) -> CodeBlock:
        if kpts:
            kpts_str = str(kpts)
            code = f"""# 周期性体系 DFT 计算（Gamma 点）
kpts = {kpts_str}
mf = pbc_dft.KRKS(cell, kpts=kpts)
mf.xc = 'B3LYP'
mf.kernel()
print(f"PBC-DFT 能量: {{mf.e_tot:.10f}} Hartree")"""
        else:
            code = """# 周期性体系 DFT 计算（Gamma 点）
mf = pbc_dft.RKS(cell)
mf.xc = 'B3LYP'
mf.kernel()
print(f"PBC-DFT 能量: {mf.e_tot:.10f} Hartree")"""

        return CodeBlock(
            section="calculation",
            code=code,
            order=10,
            description="PBC-DFT 计算",
        )

    def generate_pbc_calculation(
        self,
        lattice: str = "diamond",
        a: float = 3.567,
        basis: str = "gth-szv",
        functional: str = "PBE",
        kpts: list = None,
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        blocks = [
            self._import_block(["pbc", "pbc.gto", "pbc.dft"]),
            self._pbc_molecule_block(lattice, a, basis),
            self._pbc_scf_block(kpts),
        ]

        return GeneratedCode(
            title=f"周期性体系 ({lattice}) PBC-DFT 计算",
            description=f"使用 PBC-{functional}/{basis} 计算 {lattice} 结构",
            blocks=blocks,
            run_instructions=f"pip install pyscf && python pbc_{lattice}.py",
        )

    def generate_custom(
        self,
        mol_name: str,
        method: str = "B3LYP",
        basis: str = "6-31g*",
        calc_type: str = "energy",
        solvent: Optional[str] = None,
        solvent_model: str = "PCM",
        n_states: int = 6,
        norb: int = 4,
        nelec: int = 4,
        output_file: Optional[str] = None,
        **kwargs
    ) -> GeneratedCode:
        method_lower = method.lower()

        # 激发态方法（含 ADC(2)/EOM-CCSD 的显式路由，避免落入 TDDFT）
        if "adc" in method_lower:
            return self.generate_adc(mol_name, basis, n_states, output_file, **kwargs)

        if "eom" in method_lower:
            return self.generate_eom_ccsd(mol_name, basis, n_states, output_file, **kwargs)

        if calc_type == "excited" or "tddft" in method_lower or "td-dft" in method_lower:
            return self.generate_tddft(mol_name, method, basis, n_states, output_file, **kwargs)

        # 多参考方法
        if "nevpt2" in method_lower:
            return self.generate_nevpt2(mol_name, basis, norb, nelec, output_file, **kwargs)

        if "caspt2" in method_lower:
            # PySCF 核心不含 CASPT2，采用无入侵态的 NEVPT2 作为等价替代
            return self.generate_nevpt2(
                mol_name, basis, norb, nelec, output_file,
                note="PySCF 核心不支持 CASPT2，已改用等价的 NEVPT2",
                **kwargs
            )

        if "casci" in method_lower:
            return self.generate_casci(mol_name, basis, norb, nelec, output_file, **kwargs)

        if calc_type == "casscf" or "casscf" in method_lower:
            return self.generate_casscf(mol_name, basis, norb, nelec, output_file, **kwargs)

        if calc_type == "geometry":
            return self.generate_geometry_opt(mol_name, method, basis, output_file, **kwargs)

        if calc_type == "frequency":
            return self.generate_frequency(mol_name, method, basis, output_file, **kwargs)

        if calc_type == "nbo":
            return self.generate_nbo(mol_name, method, basis, output_file, **kwargs)

        if calc_type == "solvation" and solvent:
            return self.generate_solvation(
                mol_name, method, basis, solvent, solvent_model, output_file, **kwargs
            )

        if "ccsd(t)" in method_lower or "ccsd-t" in method_lower:
            return self.generate_ccsd_t(mol_name, basis, output_file, **kwargs)

        if "ccsd" in method_lower:
            return self.generate_ccsd(mol_name, basis, output_file, **kwargs)

        if "mp2" in method_lower:
            return self.generate_mp2(mol_name, basis, output_file, **kwargs)

        if "cisd" in method_lower:
            return self.generate_cisd(mol_name, basis, output_file, **kwargs)

        if method_lower == "fci":
            return self.generate_fci(mol_name, basis, output_file, **kwargs)

        if method_lower in ["hf", "rhf", "uhf", "rohf"]:
            result = self.generate_scf(mol_name, method, basis, output_file, **kwargs)
        else:
            try:
                result = self.generate_dft(mol_name, method, basis, output_file, **kwargs)
            except KeyError:
                raise ValueError(
                    f"暂不支持自动生成方法 '{method}' 的代码。"
                    "已支持：HF/RHF/UHF、DFT 泛函、MP2、CCSD、CCSD(T)、"
                    "CISD、FCI、CASSCF、CASCI、NEVPT2、CASPT2(→NEVPT2)、"
                    "TDDFT、ADC(2)、EOM-CCSD。"
                )

        if solvent:
            solv_block = self._solvation_block(solvent_model, solvent)
            result.blocks.append(solv_block)
            solvent_info = get_solvent(solvent)
            result.title += f" (溶剂: {solvent_info.name_cn}, {solvent_model})"

        return result
