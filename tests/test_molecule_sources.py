"""
测试外部分子源模块。
"""

import os
import tempfile
import pytest
from frank.molecule_sources import (
    search_pubchem,
    load_xyz_file,
    xyz_string_to_molecule,
    resolve_molecule,
    _parse_sdf_atoms,
    _build_formula,
)
from frank.molecules import get_molecule, MOLECULES


# ============================================================
#  XYZ 字符串解析
# ============================================================

class TestXYZParsing:
    """测试 XYZ 字符串解析。"""

    def test_standard_xyz(self):
        """标准 XYZ 格式（原子数 + 标题 + 坐标）。"""
        xyz = """3
water molecule
O  0.000  0.000  0.117
H  0.000  0.757 -0.469
H  0.000 -0.757 -0.469
"""
        mol = xyz_string_to_molecule(xyz, name="test_water")
        assert mol is not None
        assert mol.formula == "H2O"
        assert mol.atom_count == 3
        assert mol.electrons == 10

    def test_bare_xyz(self):
        """纯坐标格式（无原子数和标题行）。"""
        xyz = """O  0.000  0.000  0.117
H  0.000  0.757 -0.469
H  0.000 -0.757 -0.469
"""
        mol = xyz_string_to_molecule(xyz, name="bare_water")
        assert mol is not None
        assert mol.formula == "H2O"

    def test_empty_string(self):
        """空字符串返回 None。"""
        assert xyz_string_to_molecule("") is None

    def test_invalid_format(self):
        """无效格式返回 None。"""
        assert xyz_string_to_molecule("not xyz data") is None

    def test_carbon_dioxide(self):
        """CO2 测试。"""
        xyz = """3
CO2
C  0.000  0.000  0.000
O  0.000  0.000  1.162
O  0.000  0.000 -1.162
"""
        mol = xyz_string_to_molecule(xyz)
        assert mol is not None
        assert mol.formula == "CO2"
        assert mol.electrons == 22


# ============================================================
#  XYZ 文件加载
# ============================================================

class TestXYZFileLoading:
    """测试 XYZ 文件加载。"""

    def test_load_xyz_file(self):
        """从临时文件加载 XYZ。"""
        xyz_content = """3
water
O  0.000  0.000  0.117
H  0.000  0.757 -0.469
H  0.000 -0.757 -0.469
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xyz", delete=False) as f:
            f.write(xyz_content)
            f.flush()
            filepath = f.name

        try:
            mol = load_xyz_file(filepath)
            assert mol is not None
            assert mol.formula == "H2O"
            assert "from_xyz" in mol.tags
        finally:
            os.unlink(filepath)

    def test_nonexistent_file(self):
        """不存在的文件返回 None。"""
        assert load_xyz_file("/nonexistent/path.xyz") is None


# ============================================================
#  SDF 解析
# ============================================================

class TestSDFParsing:
    """测试 SDF 原子坐标解析。"""

    def test_parse_sdf_v2000(self):
        """解析 V2000 格式 SDF。"""
        sdf = """caffeine
  -OEChem-06162609573D

  3  2  0     0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.5000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
   -0.7500    1.2990    0.0000 N   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  2  0  0  0  0
  1  3  1  0  0  0  0
M  END
$$$$
"""
        atoms = _parse_sdf_atoms(sdf)
        assert len(atoms) == 3
        assert atoms[0][0] == "C"
        assert atoms[1][0] == "O"
        assert atoms[2][0] == "N"


# ============================================================
#  分子式生成
# ============================================================

class TestFormulaBuilding:
    """测试分子式生成。"""

    def test_hill_order(self):
        """Hill 顺序：C 先，H 次，其余字母序。"""
        atoms = [("C", 0, 0, 0), ("H", 0, 0, 1), ("H", 0, 1, 0), ("O", 1, 0, 0)]
        formula = _build_formula(atoms)
        assert formula == "CH2O"

    def test_no_carbon(self):
        """无碳分子。"""
        atoms = [("N", 0, 0, 0), ("H", 0, 0, 1), ("H", 0, 1, 0), ("H", 1, 0, 0)]
        formula = _build_formula(atoms)
        assert formula == "H3N"


# ============================================================
#  PubChem 查询（需要网络）
# ============================================================

class TestPubChem:
    """测试 PubChem API 查询。"""

    @pytest.mark.network
    def test_search_caffeine(self):
        """搜索咖啡因。"""
        mol = search_pubchem("caffeine")
        assert mol is not None
        assert mol.formula == "C8H10N4O2"
        assert mol.smiles != ""
        assert mol.atom_count > 0
        assert mol.electrons > 0

    @pytest.mark.network
    def test_search_water(self):
        """搜索水。"""
        mol = search_pubchem("water")
        assert mol is not None
        assert mol.formula == "H2O"

    @pytest.mark.network
    def test_search_nonexistent(self):
        """搜索不存在的分子。"""
        mol = search_pubchem("xyznonexistentmolecule12345")
        assert mol is None


# ============================================================
#  统一解析入口
# ============================================================

class TestResolveMolecule:
    """测试统一分子解析。"""

    @pytest.mark.network
    def test_resolve_pubchem(self):
        """通过 PubChem 解析。"""
        mol = resolve_molecule("aspirin")
        assert mol is not None
        assert "aspirin" in mol.name

    def test_resolve_xyz_string(self):
        """通过 SMILES 字符串解析（带特殊字符的才走 SMILES 通道）。"""
        # 纯 SMILES 不含特殊字符，不会被 _try_smiles 识别
        # 但 c1ccccc1 包含数字和环标记，会被识别
        mol = resolve_molecule("c1ccccc1")
        assert mol is not None

    def test_resolve_file_path(self):
        """通过文件路径解析。"""
        xyz_content = """2
H2
H  0.000  0.000  0.000
H  0.000  0.000  0.741
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xyz", delete=False) as f:
            f.write(xyz_content)
            f.flush()
            filepath = f.name

        try:
            mol = resolve_molecule(filepath)
            assert mol is not None
            assert mol.formula == "H2"
        finally:
            os.unlink(filepath)


# ============================================================
#  与 get_molecule 集成
# ============================================================

class TestGetMoleculeIntegration:
    """测试与 get_molecule 的集成。"""

    def test_builtin_molecule(self):
        """内置分子仍然正常工作。"""
        mol = get_molecule("h2o")
        assert mol.name == "h2o"
        assert mol.formula == "H2O"

    @pytest.mark.network
    def test_pubchem_fallback(self):
        """数据库中没有的分子通过 PubChem 查询。"""
        mol = get_molecule("caffeine")
        assert mol is not None
        assert mol.formula == "C8H10N4O2"
        # 查询后应注册到数据库
        assert "caffeine" in MOLECULES

    def test_xyz_file_fallback(self):
        """通过文件路径查询。"""
        xyz_content = """2
test_he
He  0.000  0.000  0.000
He  0.000  0.000  1.000
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xyz", delete=False) as f:
            f.write(xyz_content)
            f.flush()
            filepath = f.name

        try:
            mol = get_molecule(filepath)
            assert mol is not None
            assert mol.formula == "He2"
        finally:
            os.unlink(filepath)
