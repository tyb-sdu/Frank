from typing import Optional

try:
    import plotext as plt
    HAS_PLT = True
except ImportError:
    HAS_PLT = False


def _check_plotext():
    if not HAS_PLT:
        raise ImportError(
            "需要安装 plotext: pip install plotext\n"
            "  或: pip install frank[plot]"
        )


def plot_energy_levels(result, title: str = "分子轨道能级图"):
    _check_plotext()

    if not result.mo_energies:
        print("[WARN] 无轨道能量数据，跳过能级图")
        return

    energies = list(result.mo_energies)
    occ = list(result.mo_occ) if result.mo_occ else [0] * len(energies)

    n_occ = sum(1 for o in occ if o > 0)
    start = max(0, n_occ - 5)
    end = min(len(energies), n_occ + 6)
    energies_slice = energies[start:end]
    occ_slice = occ[start:end]

    energies_ev = [e * 27.2114 for e in energies_slice]

    labels = []
    colors = []
    for i, (e, o) in enumerate(zip(energies_slice, occ_slice)):
        idx = start + i
        if idx == n_occ - 1:
            labels.append("HOMO")
            colors.append("green" if o > 0 else "red")
        elif idx == n_occ:
            labels.append("LUMO")
            colors.append("red" if o == 0 else "green")
        else:
            labels.append(f"MO{idx+1}")
            colors.append("green" if o > 0 else "blue")

    plt.clear_figure()
    plt.title(title)
    plt.xlabel("能量 (eV)")

    for i, (label, e, c) in enumerate(zip(labels, energies_ev, colors)):
        plt.bar([label], [e], color=c, orientation="horizontal", width=0.6)

    if result.homo is not None and result.lumo is not None:
        gap = result.gap
        plt.xlabel(f"能量 (eV)  |  HOMO-LUMO 能隙: {gap:.2f} eV")

    plt.show()


def plot_uv_vis(result, title: str = "UV-Vis 吸收光谱"):
    _check_plotext()

    if not result.excitation_energies:
        print("[WARN] 无激发态数据，跳过光谱图")
        return

    wavelengths = result.wavelengths
    strengths = result.oscillator_strengths

    n = min(len(wavelengths), len(strengths))
    wavelengths = wavelengths[:n]
    strengths = strengths[:n]

    plt.clear_figure()
    plt.title(title)
    plt.xlabel("波长 (nm)")
    plt.ylabel("振子强度 (f)")

    labels = [f"S{i+1}\n{w:.0f}" for i, w in enumerate(wavelengths)]
    plt.bar(labels, strengths, color="blue", width=0.5)

    plt.show()

    print(f"\n光谱摘要:")
    for i, (w, f) in enumerate(zip(wavelengths, strengths)):
        if f < 0.001:
            strength = "禁阻"
        elif f < 0.01:
            strength = "弱"
        elif f < 0.1:
            strength = "中等"
        else:
            strength = "强"
        print(f"  S{i+1}: {w:.1f} nm  f={f:.4f} ({strength})")


def plot_ir_spectrum(result, title: str = "IR 振动光谱"):
    _check_plotext()

    if not result.frequencies:
        print("[WARN] 无频率数据，跳过光谱图")
        return

    freqs = result.frequencies

    real_freqs = [f for f in freqs if f > 0]

    if not real_freqs:
        print("[WARN] 无正频率数据，跳过光谱图")
        return

    bin_size = 50
    min_f = max(0, int(min(real_freqs) / bin_size) * bin_size)
    max_f = int(max(real_freqs) / bin_size) * bin_size + bin_size

    bins = list(range(min_f, max_f + 1, bin_size))
    counts = [0] * (len(bins) - 1)
    for f in real_freqs:
        idx = int((f - min_f) / bin_size)
        if 0 <= idx < len(counts):
            counts[idx] += 1

    bin_labels = [f"{b}" for b in bins[:-1]]

    plt.clear_figure()
    plt.title(title)
    plt.xlabel("频率 (cm⁻¹)")
    plt.ylabel("振动模式数")

    plt.bar(bin_labels, counts, color="red", width=0.5)

    plt.show()

    print(f"\n频率摘要:")
    print(f"  振动模式数: {len(freqs)}")
    if result.n_imaginary > 0:
        print(f"  [WARN] 虚频数: {result.n_imaginary}")
        for f in result.imaginary_freqs:
            print(f"    {f:.1f} cm⁻¹")
    else:
        print(f"  [OK] 无虚频")

    oh = [f for f in real_freqs if 3200 < f < 3700]
    ch = [f for f in real_freqs if 2800 < f < 3200]
    co = [f for f in real_freqs if 1650 < f < 1800]
    if oh:
        print(f"  O-H 伸缩: {', '.join(f'{f:.0f}' for f in oh)} cm⁻¹")
    if ch:
        print(f"  C-H 伸缩: {', '.join(f'{f:.0f}' for f in ch)} cm⁻¹")
    if co:
        print(f"  C=O 伸缩: {', '.join(f'{f:.0f}' for f in co)} cm⁻¹")


def plot_ir_with_reference(
    result,
    reference_peaks: list,
    title: str = "IR 光谱 (计算 vs 实验)",
):
    """Plot calculated IR with experimental reference peaks overlaid."""
    _check_plotext()

    if not result.frequencies:
        print("[WARN] 无频率数据，跳过光谱图")
        return

    real_freqs = sorted(f for f in result.frequencies if f > 0)
    if not real_freqs:
        return

    bin_size = 50
    min_f = max(0, int(min(real_freqs) / bin_size) * bin_size)
    max_f = max(
        int(max(real_freqs) / bin_size) * bin_size + bin_size,
        int(max((p.frequency for p in reference_peaks), default=0) / bin_size) * bin_size + bin_size,
    )

    bins = list(range(min_f, max_f + 1, bin_size))
    counts = [0] * (len(bins) - 1)
    for f in real_freqs:
        idx = int((f - min_f) / bin_size)
        if 0 <= idx < len(counts):
            counts[idx] += 1

    bin_labels = [f"{b}" for b in bins[:-1]]
    plt.clear_figure()
    plt.title(title)
    plt.xlabel("频率 (cm⁻¹)")
    plt.ylabel("振动模式数")
    plt.bar(bin_labels, counts, color="red", width=0.5)

    if reference_peaks:
        ref_labels = [f"R{p.frequency:.0f}" for p in reference_peaks[:8]]
        ref_counts = [1] * len(ref_labels)
        print(f"\n  实验参考峰 ({len(reference_peaks)} 个):")
        for p in reference_peaks[:8]:
            assign = f" ({p.assignment})" if getattr(p, "assignment", "") else ""
            print(f"    {p.frequency:.0f} cm⁻¹{assign}")

    plt.show()


def plot_method_comparison(workflow_result, title: str = "方法对比"):
    _check_plotext()

    methods = []
    energies = []
    for step in workflow_result.steps:
        if step.status == "success" and step.parsed:
            scf = step.parsed.get("scf")
            if scf and scf.energy:
                method = step.name.replace("calc_", "")
                methods.append(method)
                energies.append(scf.energy)

    if not methods:
        print("[WARN] 无成功计算结果，跳过对比图")
        return

    plt.clear_figure()
    plt.title(title)
    plt.xlabel("计算方法")
    plt.ylabel("能量 (Hartree)")

    plt.bar(methods, energies, color="cyan", width=0.5)
    plt.show()

    if len(energies) >= 2:
        print(f"\n能量差 (kcal/mol):")
        for i in range(len(methods)):
            for j in range(i + 1, len(methods)):
                de = (energies[j] - energies[i]) * 627.509
                print(f"  {methods[j]} - {methods[i]} = {de:+.4f}")


def plot_basis_convergence(workflow_result, title: str = "基组收敛性"):
    _check_plotext()

    basis_sets = []
    energies = []
    for step in workflow_result.steps:
        if step.status == "success" and step.parsed:
            scf = step.parsed.get("scf")
            if scf and scf.energy:
                basis = step.name.replace("basis_", "")
                basis_sets.append(basis)
                energies.append(scf.energy)

    if not basis_sets:
        print("[WARN] 无成功计算结果，跳过收敛图")
        return

    ref = energies[0]
    delta_e = [(e - ref) * 627.509 for e in energies]

    plt.clear_figure()
    plt.title(title)
    plt.xlabel("基组")
    plt.ylabel("ΔE (kcal/mol)")

    plt.plot(basis_sets, delta_e, marker="braille", color="green")
    plt.show()

    if len(delta_e) >= 2:
        last_diff = abs(delta_e[-1] - delta_e[-2])
        if last_diff < 0.1:
            print(f"\n[OK] 基组已收敛 (最后两级差 < 0.1 kcal/mol)")
        else:
            print(f"\n[WARN] 基组可能未收敛 (最后两级差 = {last_diff:.4f} kcal/mol)")


def plot_orbital_occupation(result, title: str = "轨道占据"):
    _check_plotext()

    if not result.mo_occ:
        print("[WARN] 无占据数据，跳过占据图")
        return

    occ = list(result.mo_occ)
    n_occ = sum(1 for o in occ if o > 0)

    start = max(0, n_occ - 4)
    end = min(len(occ), n_occ + 5)
    occ_slice = occ[start:end]

    labels = []
    for i in range(start, end):
        if i == n_occ - 1:
            labels.append("HOMO")
        elif i == n_occ:
            labels.append("LUMO")
        else:
            labels.append(f"MO{i+1}")

    electron_counts = [min(o, 2) for o in occ_slice]

    plt.clear_figure()
    plt.title(title)
    plt.xlabel("轨道")
    plt.ylabel("电子数")

    colors = ["green" if o > 0 else "gray" for o in occ_slice]
    plt.bar(labels, electron_counts, color=colors, width=0.5)

    plt.show()


def plot_result(parsed: dict, method: str = ""):
    if not HAS_PLT:
        return

    if "tddft" in parsed:
        plot_uv_vis(parsed["tddft"])

    if "frequency" in parsed:
        plot_ir_spectrum(parsed["frequency"])

    if "scf" in parsed:
        scf = parsed["scf"]
        if scf.mo_energies:
            plot_energy_levels(scf)
