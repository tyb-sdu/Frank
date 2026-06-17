"""
分子数据库测试。
"""

import pytest
from frank.molecules import (
    get_molecule, list_molecules, search_molecules,
    get_xyz_block, get_pyscf_geometry, list_tags,
)


class TestMoleculeDatabase:
    """分子数据库测试类"""

    def test_get_molecule_by_name(self):
        """测试通过英文名获取分子"""
        mol = get_molecule("h2o")
        assert mol.name == "h2o"
        assert mol.name_cn == "水"
        assert mol.formula == "H2O"
        assert mol.electrons == 10

    def test_get_molecule_by_chinese_name(self):
        """测试通过中文名获取分子"""
        mol = get_molecule("水")
        assert mol.name == "h2o"

    def test_get_molecule_by_formula(self):
        """测试通过分子式获取分子"""
        mol = get_molecule("H2O")
        assert mol.name == "h2o"

    def test_get_molecule_not_found(self):
        """测试获取不存在的分子"""
        with pytest.raises(KeyError):
            get_molecule("不存在的分子")

    def test_list_molecules(self):
        """测试列出所有分子"""
        molecules = list_molecules()
        assert len(molecules) > 20  # 至少有20个分子
        # 检查排序
        for i in range(len(molecules) - 1):
            assert (molecules[i].electrons or 0) <= (molecules[i+1].electrons or 0)

    def test_list_molecules_by_tag(self):
        """测试按标签筛选分子"""
        aromatic = list_molecules(tag="aromatic")
        assert len(aromatic) > 0
        for mol in aromatic:
            assert "aromatic" in mol.tags

    def test_search_molecules(self):
        """测试搜索分子"""
        results = search_molecules("水")
        assert len(results) > 0
        assert any(mol.name == "h2o" for mol in results)

    def test_get_xyz_block(self):
        """测试获取 XYZ 坐标"""
        mol = get_molecule("h2o")
        xyz = get_xyz_block(mol)
        assert "O" in xyz
        assert "H" in xyz
        assert "3" in xyz  # 原子数

    def test_get_pyscf_geometry(self):
        """测试获取 PySCF 几何"""
        mol = get_molecule("h2o")
        geom = get_pyscf_geometry(mol)
        assert "O" in geom
        assert "H" in geom

    def test_list_tags(self):
        """测试列出所有标签"""
        tags = list_tags()
        assert len(tags) > 5
        assert "diatomic" in tags
        assert "aromatic" in tags

    def test_molecule_multiplicity(self):
        """测试自旋多重度"""
        # 单重态
        mol = get_molecule("h2o")
        assert mol.multiplicity == 1

        # 三重态 O2
        mol = get_molecule("o2")
        assert mol.multiplicity == 3

    def test_molecule_atom_count(self):
        """测试原子计数"""
        assert get_molecule("h2").atom_count == 2
        assert get_molecule("h2o").atom_count == 3
        assert get_molecule("ch4").atom_count == 5
        assert get_molecule("c6h6").atom_count == 12

    def test_all_molecules_have_required_fields(self):
        """测试所有分子都有必要字段"""
        for mol in list_molecules():
            assert mol.name
            assert mol.name_cn
            assert mol.formula
            assert mol.smiles
            assert mol.atom_xyz.strip()
