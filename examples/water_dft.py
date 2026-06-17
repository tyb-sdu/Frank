"""
示例：水分子 B3LYP/6-31G* 几何优化

使用 Frank 生成的代码，可直接运行。
"""

# ============================================================
#  导入模块
# ============================================================
from pyscf import gto, dft

# ============================================================
#  基组设置
# ============================================================
BASIS = "6-31g*"

# ============================================================
#  分子定义
# ============================================================
# 水 (H2O)
mol = gto.Mole()
mol.atom = '''
    O  0.000  0.000  0.117
    H  0.000  0.757 -0.469
    H  0.000 -0.757 -0.469
'''
mol.basis = BASIS
mol.charge = 0
mol.spin = 0  # 自旋多重度 = 1 (单重态)
mol.verbose = 4
mol.build()

# ============================================================
#  DFT 计算
# ============================================================
mf = dft.RKS(mol)
mf.xc = 'B3LYP'
mf.kernel()

print(f"DFT (B3LYP) 能量: {mf.e_tot:.10f} Hartree")

# ============================================================
#  几何优化
# ============================================================
from pyscf.geomopt.geometric_solver import optimize

print("\n开始几何优化...")
mol_eq = optimize(mf, maxsteps=100)

print(f"\n优化后能量: {mf.e_tot:.10f} Hartree")
print("优化后几何 (Angstrom):")
coords = mol_eq.atom_coords() * 0.529177
for i, (symbol, coord) in enumerate(zip(mol_eq.elements, coords)):
    print(f"  {symbol:2s}  {coord[0]:10.6f}  {coord[1]:10.6f}  {coord[2]:10.6f}")

# ============================================================
#  频率计算
# ============================================================
print("\n计算振动频率...")
from pyscf.hessian import thermo

hessian = mf.Hessian()
hessian.kernel()

freq_analysis = thermo.harmonic_analysis(mol, hessian)
print(f"振动频率 (cm^-1): {freq_analysis['freq_energy']}")
print(f"零点能: {freq_analysis['ZPE'][0]:.6f} Hartree")
