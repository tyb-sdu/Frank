import re
from typing import Optional

SCRIPT_HEADER = '''import json
import sys
import numpy as np
_FRANK_RESULTS = {}

'''

SCRIPT_FOOTER = '''

import json
import numpy as np

try:
    _results = {}

    try:
        _results["energy"] = float(mf.e_tot)
    except Exception:
        pass

    try:
        _results["converged"] = bool(mf.converged)
    except Exception:
        pass

    try:
        mo_e = mf.mo_energy
        mo_o = mf.mo_occ
        if isinstance(mo_e, np.ndarray) and mo_e.ndim == 2:
            _results["mo_energy_alpha"] = mo_e[0].tolist()
            _results["mo_energy_beta"] = mo_e[1].tolist()
            _results["mo_occ_alpha"] = mo_o[0].tolist()
            _results["mo_occ_beta"] = mo_o[1].tolist()
        else:
            _results["mo_energy"] = np.array(mo_e).tolist()
            _results["mo_occ"] = np.array(mo_o).tolist()
    except Exception:
        pass

    try:
        dip = mf.dip_moment()
        _results["dipole"] = np.array(dip).tolist()
    except Exception:
        pass

    try:
        grad = mf.Gradients().grad()
        _results["gradient"] = np.array(grad).tolist()
    except Exception:
        pass

    print("\\n_FRANK_RESULT_JSON:" + json.dumps(_results))

except Exception as e:
    print(f"\\n_FRANK_RESULT_ERROR: {str(e)}")
'''


def enhance_script(script: str) -> str:
    return SCRIPT_HEADER + script + SCRIPT_FOOTER


def classify_error(stderr: str, stdout: str) -> tuple[str, str]:
    combined = (stderr + stdout).lower()

    if "max cycle" in combined or "convergence" in combined or "scf not converged" in combined:
        return "scf_convergence", "SCF 迭代未收敛，建议：1) 增加 max_cycle 2) 使用 DIIS 3) 换初始猜测"

    if "memory" in combined or "oom" in combined or "killed" in combined:
        return "memory", "内存不足，建议：1) 减小基组 2) 使用密度拟合 (DF) 3) 增加系统内存"

    if "basis" in combined and ("not found" in combined or "error" in combined):
        return "basis_error", "基组定义错误，建议检查基组名称拼写"

    if "integral" in combined or "eri" in combined:
        return "integral_error", "积分计算错误，可能是分子几何有问题"

    if "linear dependence" in combined or "lineardep" in combined:
        return "linear_dep", "基组线性依赖，建议：1) 删除弥散函数 2) 使用正交化基组"

    if "atom" in combined and ("too close" in combined or "overlap" in combined):
        return "geometry", "原子距离过近，建议检查分子几何"

    if "traceback" in combined:
        lines = stderr.strip().split("\n")
        last_error = lines[-1] if lines else "未知 Python 错误"
        return "python_error", last_error

    return "unknown", stderr[:200] if stderr else "未知错误"


def extract_results_from_stdout(stdout: str) -> dict:
    import json

    for line in reversed(stdout.split("\n")):
        if "_FRANK_RESULT_JSON:" in line:
            json_str = line.split("_FRANK_RESULT_JSON:", 1)[1].strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

    return {}


def extract_errors_from_stdout(stdout: str) -> Optional[str]:
    for line in reversed(stdout.split("\n")):
        if "_FRANK_RESULT_ERROR:" in line:
            return line.split("_FRANK_RESULT_ERROR:", 1)[1].strip()
    return None
