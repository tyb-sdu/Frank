"""pytest 共享配置与夹具。

关键作用：隔离全局分子数据库 `MOLECULES`。部分测试会通过 PubChem/SMILES/XYZ
把新分子注册进全局字典，这些外部分子可能缺少 name_cn/smiles 等字段，若不隔离
会污染其他测试（例如 test_all_molecules_have_required_fields）。
"""

import copy

import pytest

from frank.molecules import database as _db


@pytest.fixture(autouse=True)
def _isolate_molecule_registry():
    """每个测试前后快照并恢复全局 MOLECULES，避免跨测试污染。"""
    snapshot = copy.copy(_db.MOLECULES)
    try:
        yield
    finally:
        _db.MOLECULES.clear()
        _db.MOLECULES.update(snapshot)
