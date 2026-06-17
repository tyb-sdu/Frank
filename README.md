# Frank — 计算化学终端智能体

<div align="center">

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ███████╗██████╗  █████╗ ███╗   ██╗██╗  ██╗              ║
║     ██╔════╝██╔══██╗██╔══██╗████╗  ██║██║ ██╔╝              ║
║     █████╗  ██████╔╝███████║██╔██╗ ██║█████╔╝               ║
║     ██╔══╝  ██╔══██╗██╔══██║██║╚██╗██║██╔═██╗               ║
║     ██║     ██║  ██║██║  ██║██║ ╚████║██║  ██╗              ║
║     ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝              ║
║                                                              ║
║          计算化学终端智能体 v0.2.0                             ║
║          能生成、能执行、能诊断、能解读                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![PySCF](https://img.shields.io/badge/PySCF-2.4+-green.svg)](https://pyscf.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

## 🧪 简介

Frank 是一个**计算化学终端智能体**。你只需用自然语言描述计算需求，Frank 就会：

1. **生成代码** — 自动生成可运行的 PySCF Python 代码
2. **执行计算** — 直接运行计算并返回结果
3. **智能诊断** — 检测 SCF 收敛、基组选择、虚频等问题
4. **结果解读** — 用人话告诉你计算结果的化学含义
5. **工作流自动化** — 几何优化→频率验证→高精度单点，自动串联

**Frank 不只是一个代码生成器，它是一个能替代计算化学研究生的智能体。**

## ✨ 核心能力

### 🚀 执行与诊断

| 能力 | 说明 |
|------|------|
| **代码生成** | 根据自然语言生成可运行的 PySCF 代码 |
| **直接执行** | 调用 PySCF 执行计算，返回结构化结果 |
| **智能诊断** | SCF 不收敛？基组太小？有虚频？自动检测并给出修复建议 |
| **结果解读** | 用人话解读能量、轨道、频率、激发态的化学含义 |
| **工作流自动化** | 几何优化→频率验证→高精度单点，自动串联 |

### 🔬 支持的计算方法

| 类别 | 方法 |
|------|------|
| **SCF** | HF, RHF, UHF, ROHF |
| **DFT** | B3LYP, PBE, PBE0, M06-2X, wB97X-D, CAM-B3LYP, HSE06 等 30+ 泛函 |
| **后 HF** | MP2, CCSD, CCSD(T), DF-MP2, DF-CCSD |
| **激发态** | TDDFT, TDA, CIS, ADC(2), EOM-CCSD |
| **多参考态** | CASSCF, CASCI, NEVPT2, CASPT2, DMRG-CASSCF |
| **溶剂化** | PCM, CPCM, SMD, COSMO |

### 🧫 内置分子数据库

- **50+ 常见分子**的 3D 坐标
- 覆盖：双原子分子、小分子、有机分子、离子、自由基
- 支持中英文名称、分子式、SMILES 查询

### 📐 基组支持

- **劈裂价层**: 6-31G*, 6-311G**, 6-31+G*, 6-31++G**
- **Dunning 相关一致**: cc-pVDZ, cc-pVTZ, cc-pVQZ, aug-cc-pVDZ
- **Ahlrichs**: def2-SVP, def2-TZVP, def2-QZVP
- **赝势**: LANL2DZ

### 🎯 智能推荐

- 自动推荐基组（根据方法和精度要求）
- 自动选择 SCF 类型（RHF/UHF 根据自旋）
- 自动推断 CASSCF 活性空间
- 自动推荐 DFT 泛函（根据计算目的）

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/frank-chem/frank.git
cd frank

# 安装依赖
pip install -e .

# 或者只安装依赖
pip install pyscf rich click
```

### 使用方式

#### 1. 交互模式

```bash
python run.py
# 或
frank
```

然后直接输入计算需求：

```
Frank> 计算水分子在 B3LYP/6-31G* 水平的能量
Frank> 用 MP2/cc-pVDZ 计算氨的几何优化
Frank> 计算苯的 TDDFT 激发态（6个态）
Frank> 用 CASSCF(6,6)/cc-pVDZ 计算氮气
```

#### 2. 命令行模式

```bash
# 仅生成代码（不执行）
python run.py ask "计算水分子的 B3LYP 能量"

# 执行计算（生成代码 + 运行 + 解读结果）
python run.py run "计算水分子的 B3LYP 能量"

# 运行工作流
python run.py workflow opt_freq h2o --method B3LYP --basis 6-31g*
python run.py workflow method_comparison h2o --methods HF,B3LYP,MP2
python run.py workflow basis_convergence h2o --method B3LYP --basis-sets 6-31g*,cc-pvdz,cc-pvtz

# 列出可用分子
frank list molecules

# 列出可用方法
frank list methods

# 列出可用基组
frank list basis

# 列出可用溶剂
frank list solvents

# 查看分子信息
frank info h2o
frank info 水

# 显示 XYZ 坐标
frank xyz h2o
```

#### 3. Python API

```python
from frank.agent import FrankAgent

agent = FrankAgent()
result = agent.process_request("计算水分子的 B3LYP 能量")

# 获取生成的代码
print(result["script"])

# 获取解析的意图
print(result["intent"].molecule)  # "h2o"
print(result["intent"].method)    # "B3LYP"
```

## 📖 使用示例

### 示例 1: 单点能计算

**输入:**
```
计算水分子在 B3LYP/6-31G* 水平的能量
```

**生成代码:**
```python
from pyscf import gto, dft

BASIS = "6-31g*"

mol = gto.Mole()
mol.atom = '''
    O  0.000  0.000  0.117
    H  0.000  0.757 -0.469
    H  0.000 -0.757 -0.469
'''
mol.basis = BASIS
mol.charge = 0
mol.spin = 0
mol.verbose = 4
mol.build()

mf = dft.RKS(mol)
mf.xc = 'B3LYP'
mf.kernel()

print(f"DFT (B3LYP) 能量: {mf.e_tot:.10f} Hartree")
```

### 示例 2: 几何优化

**输入:**
```
优化氨分子的几何结构，使用 MP2/cc-pVDZ
```

### 示例 3: 激发态计算

**输入:**
```
计算苯的 TDDFT 激发态，B3LYP/6-31G*，6个态
```

### 示例 4: CASSCF 计算

**输入:**
```
用 CASSCF(6,6)/cc-pVDZ 计算氮气
```

### 示例 5: 溶剂化计算

**输入:**
```
计算乙醇在水中的溶剂化能，使用 PCM 模型
```

## 📁 项目结构

```
frank/
├── __init__.py              # 包初始化
├── agent.py                 # 核心智能体（意图解析 + 代码生成）
├── cli.py                   # CLI 界面
├── molecules.py             # 分子数据库（50+ 分子）
├── basis_sets.py            # 基组配置
├── methods/
│   ├── __init__.py
│   ├── scf.py              # SCF 方法定义
│   ├── dft.py              # DFT 泛函定义（30+ 泛函）
│   ├── post_hf.py          # 后 HF 方法（MP2, CCSD, CCSD(T)）
│   ├── excited.py          # 激发态方法（TDDFT, EOM-CCSD）
│   ├── casscf.py           # 多参考态方法（CASSCF, NEVPT2）
│   └── solvation.py        # 溶剂化模型（PCM, SMD）
├── templates/
│   ├── __init__.py
│   ├── base.py             # 模板引擎基类
│   └── pyscf_templates.py  # PySCF 代码模板
examples/
│   ├── water_hf.py         # 水分子 HF 示例
│   ├── water_dft.py        # 水分子 DFT 几何优化
│   ├── benzene_tddft.py    # 苯的 TDDFT 示例
│   ├── nh3_mp2.py          # 氨的 MP2 示例
│   └── n2_casscf.py        # 氮气 CASSCF 示例
tests/
    ├── test_molecules.py   # 分子数据库测试
    ├── test_agent.py       # 智能体测试
    └── test_templates.py   # 模板引擎测试
```

## 🧠 智能特性

### 自然语言理解

Frank 能理解多种表达方式：

- "计算水分子的能量" → HF/6-31G* 单点能
- "用 B3LYP 优化氨的结构" → B3LYP/6-31G* 几何优化
- "MP2/cc-pVDZ 计算甲烷" → MP2/cc-pVDZ 单点能
- "苯的 6 个激发态" → B3LYP/6-31G* TDDFT
- "CASSCF(4,4) 计算乙烯" → CASSCF(4,4)/cc-pVDZ

### 智能参数推荐

当用户未指定参数时，Frank 会自动推荐：

| 场景 | 推荐基组 |
|------|----------|
| HF/DFT 通用计算 | 6-31G* |
| 后 HF 方法 | cc-pVDZ |
| 激发态计算 | 6-31+G* |
| 高精度计算 | cc-pVTZ |
| 阴离子/弱相互作用 | aug-cc-pVDZ |

### 自动方法选择

| 分子状态 | 推荐 SCF 类型 |
|----------|--------------|
| 闭壳层 (spin=0) | RHF / RKS |
| 开壳层 (spin>0) | UHF / UKS |

## 🔧 扩展

### 添加新分子

在 `frank/molecules.py` 中添加：

```python
_molecules.append(Molecule(
    name="my_mol",
    name_cn="我的分子",
    formula="C2H4",
    smiles="C=C",
    atom_xyz="""
    C  0.000  0.000  0.000
    C  0.000  0.000  1.340
    H  0.000  0.930 -0.590
    H  0.000 -0.930 -0.590
    H  0.000  0.930  1.930
    H  0.000 -0.930  1.930
    """,
    electrons=16,
    tags=["alkene", "planar"],
))
```

### 添加新泛函

在 `frank/methods/dft.py` 中添加：

```python
_dft_functionals.append(DFTFunctional(
    name="MYFUNC",
    name_cn="我的泛函",
    category="hybrid",
    description="自定义泛函",
    when_to_use="特殊场景",
    accuracy="medium",
))
```

## 📚 参考资料

- [PySCF 文档](https://pyscf.org/)
- [PySCF GitHub](https://github.com/pyscf/pyscf)
- [计算化学维基百科](https://en.wikipedia.org/wiki/Computational_chemistry)
- [基组数据库](https://www.basissetexchange.org/)

## 📄 许可证

MIT License

## 🙏 致谢

- [PySCF](https://pyscf.org/) — 优秀的 Python 量子化学库
- [Rich](https://rich.readthedocs.io/) — 终端美化库
- [Click](https://click.palletsprojects.com/) — CLI 框架
