---
name: frank
description: >-
  Computational chemistry assistant powered by Frank MCP. Generates and runs
  PySCF quantum chemistry calculations. Use when the user asks about molecular
  energy, geometry optimization, frequencies, excited states, solvation,
  reaction thermochemistry, DFT/MP2/CCSD, basis sets, or mentions Frank,
  PySCF, quantum chemistry, or computational chemistry workflows.
---

# Frank — 计算化学 MCP 编排

Frank MCP 提供 20 个工具。Agent 应通过 MCP 调用，而非手写 PySCF 代码。

## 决策流程

```
用户请求
  ├─ 概念/方法问题 → frank_explain
  ├─ 查分子/方法/基组 → frank_list_* / frank_get_*
  ├─ 只需代码 → frank_generate_code
  ├─ 单次计算 → frank_run_calculation
  ├─ 多步工作流 → frank_is_complex_query
  │     ├─ 复杂 → frank_plan_workflow → 确认 → frank_run_autonomous
  │     └─ 简单 → frank_run_calculation 或 frank_run_workflow
  └─ 计算失败 → frank_diagnose_error
```

## 标准工作流

### 1. 分子准备

- 内置分子：`frank_list_molecules` 或 `frank_get_molecule`
- 外部分子：`frank_search_pubchem`（PubChem 查询并注册）
- XYZ 文件：`frank_import_molecule`

### 2. 参数确认

- 不确定基组：`frank_recommend_basis(method, calc_type, accuracy)`
- 不确定方法：`frank_list_methods` + `frank_explain`
- 溶剂效应：`frank_list_solvents` → 在 generate/run 时指定 solvent

### 3. 代码生成 vs 执行

| 场景 | 工具 |
|------|------|
| 用户只要代码 | `frank_generate_code` |
| 用户要结果 | `frank_run_calculation` |
| 优化+频率 | `frank_run_workflow(workflow_type="opt_freq")` |
| 方法对比 | `frank_run_workflow(workflow_type="method_comparison")` |
| 反应热力学 | `frank_run_autonomous` |

### 4. 复杂任务判断

先调用 `frank_is_complex_query`。若 `is_complex=true`：

1. `frank_plan_workflow` 展示计划
2. 向用户确认（涉及长时间计算时必做）
3. `frank_run_autonomous` 执行

## 重要规则

1. **优先 MCP，少写代码**：能用 Frank 工具就不自己写 PySCF 脚本。
2. **重计算先规划**：`run_autonomous` / `run_workflow` 可能耗时数分钟到数小时，执行前说明预计时间。
3. **解析意图**：自然语言请求先用 `frank_parse_intent` 确认分子、方法、基组、计算类型。
4. **错误处理**：失败时调用 `frank_diagnose_error`，结合 stdout/stderr 给出修复建议。
5. **session 上下文**：同一对话中 `frank_parse_intent(use_session=true)` 可复用上次分子/方法。

## calc_type 参考

| 类型 | 含义 |
|------|------|
| energy | 单点能量 |
| geometry | 几何优化 |
| frequency | 频率/热力学 |
| excited | TDDFT 激发态 |
| casscf | 多参考 CASSCF |
| nbo | NBO 分析 |
| solvation | 溶剂化（配合 solvent 参数） |

## workflow_type 参考

| 类型 | 用途 |
|------|------|
| opt_freq | 优化 + 频率 |
| method_comparison | 多方法对比 |
| basis_convergence | 基组收敛测试 |
| pes_scan | 势能面扫描 |
| solvation | 溶剂化自由能 |

## 输出格式

向用户展示结果时：

1. **意图摘要**：分子、方法、基组、计算类型
2. **关键数值**：能量 (Ha/kcal/mol)、几何、频率、激发能等
3. **解读**：`interpretation` 字段的自然语言说明
4. **代码**：仅在用户需要时展示 `script`
5. **警告/诊断**：显式列出 warnings 和 error_diagnosis

## 附加资源

- 完整工具参数说明：[tools-reference.md](tools-reference.md)
- 对话示例：[examples.md](examples.md)
