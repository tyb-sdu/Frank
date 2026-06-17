from typing import Optional
from .parser import SCFResult, MP2Result, CCSDResult, TDDFTResult, FrequencyResult


HARTREE_TO_EV = 27.211386
HARTREE_TO_KCAL = 627.509
HARTREE_TO_KJ = 2625.5


class ResultInterpreter:

    def interpret(self, parsed: dict, method: str = "HF", mol_name: str = "") -> str:
        if not parsed:
            return ""

        if "tddft" in parsed:
            return self.interpret_tddft(parsed["tddft"], mol_name)

        if "frequency" in parsed:
            return self.interpret_frequency(parsed["frequency"], mol_name)

        if "ccsd" in parsed:
            return self.interpret_ccsd(parsed["ccsd"], mol_name)

        if "mp2" in parsed:
            return self.interpret_mp2(parsed["mp2"], mol_name)

        if "casscf" in parsed:
            return self.interpret_casscf(parsed["casscf"], mol_name)

        if "scf" in parsed:
            return self.interpret_scf(parsed["scf"], method, mol_name)

        return ""

    def interpret_scf(self, result: SCFResult, method: str = "HF", mol_name: str = "") -> str:
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"  计算结果解读: {mol_name} ({method})")
        lines.append(f"{'='*60}\n")

        if result.energy is not None:
            lines.append(f"电子能量:")
            lines.append(f"   {result.energy:.10f} Hartree")
            lines.append(f"   = {result.energy * HARTREE_TO_EV:.6f} eV")
            lines.append(f"   = {result.energy * HARTREE_TO_KCAL:.4f} kcal/mol")
            lines.append(f"   = {result.energy * HARTREE_TO_KJ:.4f} kJ/mol")

        if result.converged:
            lines.append(f"\n[OK] SCF 收敛: 是 (迭代 {result.n_cycles} 次)")
        else:
            lines.append(f"\n[FAIL] SCF 收敛: 否 (迭代 {result.n_cycles} 次)")

        if result.mo_occ:
            n_occ = sum(1 for o in result.mo_occ if o > 0)
            n_virt = len(result.mo_occ) - n_occ
            lines.append(f"\n分子轨道:")
            lines.append(f"   占据轨道: {n_occ}")
            lines.append(f"   空轨道: {n_virt}")
            lines.append(f"   总轨道数: {len(result.mo_occ)}")

        if result.homo is not None and result.lumo is not None:
            lines.append(f"\n前线轨道:")
            lines.append(f"   HOMO 能量: {result.homo:.4f} eV")
            lines.append(f"   LUMO 能量: {result.lumo:.4f} eV")
            lines.append(f"   HOMO-LUMO 能隙: {result.gap:.4f} eV")

            if result.gap < 3:
                lines.append(f"\n   提示: 能隙较小，分子可能有颜色或导电性")
            elif result.gap > 8:
                lines.append(f"\n   提示: 能隙较大，分子较稳定，可能是绝缘体")

            if result.homo > -5:
                lines.append(f"   提示: HOMO 能量较高，分子易失去电子（还原剂）")
            elif result.homo < -10:
                lines.append(f"   提示: HOMO 能量较低，分子较稳定")

            if result.lumo < 0:
                lines.append(f"   提示: LUMO 能量较低，分子易接受电子（氧化剂）")

        if result.dipole_magnitude is not None:
            lines.append(f"\n偶极矩: {result.dipole_magnitude:.4f} Debye")

            if result.dipole:
                lines.append(f"   分量: ({result.dipole[0]:.4f}, {result.dipole[1]:.4f}, {result.dipole[2]:.4f})")

            if result.dipole_magnitude < 0.5:
                lines.append(f"   提示: 非极性或弱极性分子")
            elif result.dipole_magnitude > 2:
                lines.append(f"   提示: 强极性分子，易溶于极性溶剂")

        return "\n".join(lines)

    def interpret_mp2(self, result: MP2Result, mol_name: str = "") -> str:
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"  MP2 计算结果解读: {mol_name}")
        lines.append(f"{'='*60}\n")

        if result.hf_energy:
            lines.append(f"HF 能量: {result.hf_energy:.10f} Hartree")

        if result.mp2_corr:
            lines.append(f"MP2 相关能: {result.mp2_corr:.10f} Hartree")
            lines.append(f"             = {result.mp2_corr * HARTREE_TO_KCAL:.4f} kcal/mol")

        if result.mp2_total:
            lines.append(f"\nMP2 总能量: {result.mp2_total:.10f} Hartree")
            lines.append(f"             = {result.mp2_total * HARTREE_TO_EV:.6f} eV")

        if result.hf_energy and result.mp2_corr:
            corr_pct = abs(result.mp2_corr / result.hf_energy) * 100
            lines.append(f"\n提示: 电子相关能占总能量的 {corr_pct:.2f}%")

        return "\n".join(lines)

    def interpret_ccsd(self, result: CCSDResult, mol_name: str = "") -> str:
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"  CCSD(T) 计算结果解读: {mol_name}")
        lines.append(f"{'='*60}\n")

        if result.hf_energy:
            lines.append(f"HF 能量: {result.hf_energy:.10f} Hartree")

        if result.ccsd_corr:
            lines.append(f"CCSD 相关能: {result.ccsd_corr:.10f} Hartree")

        if result.ccsd_total:
            lines.append(f"CCSD 总能量: {result.ccsd_total:.10f} Hartree")

        if result.ccsd_t_correction:
            lines.append(f"(T) 校正: {result.ccsd_t_correction:.10f} Hartree")
            lines.append(f"           = {result.ccsd_t_correction * HARTREE_TO_KCAL:.4f} kcal/mol")

        if result.ccsd_t_total:
            lines.append(f"\nCCSD(T) 总能量: {result.ccsd_t_total:.10f} Hartree")
            lines.append(f"                 = {result.ccsd_t_total * HARTREE_TO_EV:.6f} eV")
            lines.append(f"                 = {result.ccsd_t_total * HARTREE_TO_KCAL:.4f} kcal/mol")

        lines.append(f"\n提示: CCSD(T) 是量子化学的'金标准'方法，精度很高")
        lines.append(f"   通常误差在 1 kcal/mol 以内")

        return "\n".join(lines)

    def interpret_tddft(self, result: TDDFTResult, mol_name: str = "") -> str:
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"  TDDFT 激发态解读: {mol_name}")
        lines.append(f"{'='*60}\n")

        if result.n_states == 0:
            lines.append("未找到激发态数据")
            return "\n".join(lines)

        lines.append(f"计算了 {result.n_states} 个激发态\n")

        lines.append(f"{'态':<6} {'能量 (eV)':<15} {'波长 (nm)':<15} {'振子强度':<15} {'跃迁类型'}")
        lines.append(f"{'-'*70}")

        for i in range(result.n_states):
            e = result.excitation_energies[i] if i < len(result.excitation_energies) else 0
            w = result.wavelengths[i] if i < len(result.wavelengths) else 0
            f = result.oscillator_strengths[i] if i < len(result.oscillator_strengths) else 0

            if f < 0.001:
                trans_type = "禁阻"
            elif f < 0.01:
                trans_type = "弱允许"
            elif f < 0.1:
                trans_type = "允许"
            else:
                trans_type = "强允许"

            lines.append(f"S{i+1:<4} {e:<15.4f} {w:<15.1f} {f:<15.6f} {trans_type}")

        if result.excitation_energies:
            lowest_e = result.excitation_energies[0]
            lowest_w = result.wavelengths[0] if result.wavelengths else 0

            lines.append(f"\n提示: 最低激发态: {lowest_e:.4f} eV ({lowest_w:.0f} nm)")

            if lowest_w > 700:
                lines.append(f"   提示: 吸收在红外区，分子可能无色")
            elif lowest_w > 400:
                lines.append(f"   提示: 吸收在可见光区，分子可能有颜色")
            elif lowest_w > 200:
                lines.append(f"   提示: 吸收在紫外区，分子无色但紫外吸收强")

        strong_states = [i for i, f in enumerate(result.oscillator_strengths) if f > 0.1]
        if strong_states:
            lines.append(f"\n强吸收态: S{', S'.join(str(i+1) for i in strong_states)}")

        return "\n".join(lines)

    def interpret_frequency(self, result: FrequencyResult, mol_name: str = "") -> str:
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"  频率计算结果解读: {mol_name}")
        lines.append(f"{'='*60}\n")

        n_modes = len(result.frequencies)
        lines.append(f"振动模式数: {n_modes}")

        if result.n_imaginary == 0:
            lines.append(f"\n[OK] 无虚频 — 结构为极小值点")
        elif result.n_imaginary == 1:
            lines.append(f"\n[WARN] 1 个虚频: {result.imaginary_freqs[0]:.1f} cm^-1")
            lines.append(f"   可能是过渡态")
        else:
            lines.append(f"\n[FAIL] {result.n_imaginary} 个虚频:")
            for f in result.imaginary_freqs:
                lines.append(f"   {f:.1f} cm^-1")
            lines.append(f"   结构不是极小值点，需要重新优化")

        if result.zpe is not None:
            lines.append(f"\n零点能 (ZPE): {result.zpe:.6f} Hartree")
            lines.append(f"               = {result.zpe * HARTREE_TO_KCAL:.4f} kcal/mol")

        if result.enthalpy is not None:
            lines.append(f"\n焓 (H): {result.enthalpy:.6f} Hartree")

        if result.free_energy is not None:
            lines.append(f"自由能 (G): {result.free_energy:.6f} Hartree")

            if result.enthalpy:
                ts = result.enthalpy - result.free_energy
                lines.append(f"   -TS = {ts:.6f} Hartree = {ts * HARTREE_TO_KCAL:.4f} kcal/mol")

        if result.frequencies:
            lines.append(f"\n特征振动频率:")

            oh_freqs = [f for f in result.frequencies if 3200 < f < 3700]
            if oh_freqs:
                lines.append(f"   O-H 伸缩: {', '.join(f'{f:.0f}' for f in oh_freqs)} cm^-1")

            ch_freqs = [f for f in result.frequencies if 2800 < f < 3200]
            if ch_freqs:
                lines.append(f"   C-H 伸缩: {', '.join(f'{f:.0f}' for f in ch_freqs)} cm^-1")

            co_freqs = [f for f in result.frequencies if 1650 < f < 1800]
            if co_freqs:
                lines.append(f"   C=O 伸缩: {', '.join(f'{f:.0f}' for f in co_freqs)} cm^-1")

            fingerprint = [f for f in result.frequencies if 400 < f < 1500]
            if fingerprint:
                lines.append(f"   指纹区: {len(fingerprint)} 个振动模式 (400-1500 cm^-1)")

        return "\n".join(lines)

    def interpret_workflow(self, workflow_result, mol_name: str = "", method: str = "") -> str:
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"  工作流结果总结: {mol_name}")
        lines.append(f"{'='*60}\n")

        for step in workflow_result.steps:
            status = "[OK]" if step.status == "success" else "[FAIL]"
            lines.append(f"{status} {step.description}")

            if step.parsed:
                if "scf" in step.parsed:
                    scf = step.parsed["scf"]
                    if scf.energy:
                        lines.append(f"   能量: {scf.energy:.10f} Hartree")

                if "frequency" in step.parsed:
                    freq = step.parsed["frequency"]
                    if freq.is_minimum:
                        lines.append(f"   频率: 无虚频，结构为极小值点")
                    else:
                        lines.append(f"   频率: {freq.n_imaginary} 个虚频 [WARN]")

        final_e = workflow_result.final_energy
        if final_e:
            lines.append(f"\n{'='*60}")
            lines.append(f"  最终结果")
            lines.append(f"{'='*60}")
            lines.append(f"能量: {final_e:.10f} Hartree")
            lines.append(f"    = {final_e * HARTREE_TO_EV:.6f} eV")
            lines.append(f"    = {final_e * HARTREE_TO_KCAL:.4f} kcal/mol")

        return "\n".join(lines)

    def interpret_casscf(self, result, mol_name: str = "") -> str:
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"  CASSCF 计算结果解读: {mol_name}")
        lines.append(f"{'='*60}\n")

        if result.energy is not None:
            lines.append(f"CASSCF 能量: {result.energy:.10f} Hartree")
            lines.append(f"               = {result.energy * HARTREE_TO_EV:.6f} eV")
            lines.append(f"               = {result.energy * HARTREE_TO_KCAL:.4f} kcal/mol")

        if result.n_cas_orb > 0:
            lines.append(f"\n活性空间:")
            lines.append(f"   活性轨道数: {result.n_cas_orb}")
            lines.append(f"   活性电子数: {result.n_cas_elec}")

        if result.converged:
            lines.append(f"\n[OK] CASSCF 收敛: 是")
        else:
            lines.append(f"\n[FAIL] CASSCF 收敛: 否")

        lines.append(f"\n提示: CASSCF 适合描述多参考态特征，如键断裂、双自由基等")

        return "\n".join(lines)
