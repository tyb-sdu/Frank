# Frank MCP 使用示例

## 示例 1：单点能量（只要代码）

**用户**：帮我生成水分子 B3LYP/6-31G* 单点能的 PySCF 代码

**Agent 步骤**：
1. `frank_generate_code(query="水分子 B3LYP/6-31G* 单点能")`
2. 向用户展示 `script` 和意图摘要

## 示例 2：单点能量（要结果）

**用户**：计算苯分子 HF/STO-3G 的能量

**Agent 步骤**：
1. `frank_parse_intent(query="苯分子 HF/STO-3G 能量")` — 确认意图
2. `frank_run_calculation(query="苯分子 HF/STO-3G 能量")`
3. 展示 `parsed` 中的能量和 `interpretation`

## 示例 3：外部分子

**用户**：计算咖啡因的 B3LYP/6-31G* 能量

**Agent 步骤**：
1. `frank_search_pubchem(name="caffeine")`
2. `frank_run_calculation(query="咖啡因 B3LYP/6-31G* 能量")`

## 示例 4：几何优化 + 频率

**用户**：对氨分子做 B3LYP/6-31G* 几何优化和频率计算

**Agent 步骤**：
1. `frank_run_workflow(workflow_type="opt_freq", molecule="nh3", method="B3LYP", basis="6-31g*")`
2. 展示各 step 状态和最终能量/频率

## 示例 5：方法对比

**用户**：对比 HF、B3LYP、MP2 计算水分子能量的差异

**Agent 步骤**：
1. `frank_run_workflow(workflow_type="method_comparison", molecule="h2o", methods="HF,B3LYP,MP2", basis="cc-pvdz")`

## 示例 6：反应热力学（复杂任务）

**用户**：计算 2H2 + O2 → 2H2O 的反应能

**Agent 步骤**：
1. `frank_is_complex_query(query="2H2 + O2 -> 2H2O 反应能")` — 确认 is_complex=true
2. `frank_plan_workflow(query="...")` — 展示计划，请用户确认
3. `frank_run_autonomous(query="计算 2H2 + O2 -> 2H2O 的反应能")`
4. 展示 `summary` 和各物种能量

## 示例 7：概念问答

**用户**：B3LYP 和 MP2 哪个更适合有机分子？

**Agent 步骤**：
1. `frank_explain(question="B3LYP 和 MP2 哪个更适合有机分子？")`

## 示例 8：计算失败诊断

**用户**：我的 SCF 不收敛怎么办？

**Agent 步骤**：
1. 若有具体输出：`frank_diagnose_error(stderr=..., stdout=..., job_context="h2o B3LYP/6-31g* energy")`
2. 若无输出：`frank_explain(question="SCF 不收敛的常见原因和解决方法")`

## 示例 9：基组选择

**用户**：CCSD(T) 计算苯的 energies 用什么基组好？

**Agent 步骤**：
1. `frank_recommend_basis(method="CCSD(T)", calc_type="energy", accuracy="medium")`
2. `frank_explain(question="CCSD(T) 计算苯推荐什么基组？")`

## 示例 10：激发态

**用户**：计算苯的 TDDFT 前 6 个激发态

**Agent 步骤**：
1. `frank_generate_code(molecule="c6h6", method="B3LYP", basis="6-31g*", calc_type="excited", n_states=6)`
2. 若用户要运行：`frank_run_calculation(query="苯 TDDFT 6 个激发态 B3LYP/6-31g*")`
