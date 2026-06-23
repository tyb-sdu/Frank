# Frank MCP 工具参考

## 查询类

### frank_list_molecules
| 参数 | 类型 | 说明 |
|------|------|------|
| tag | str? | 按标签过滤 |
| search | str? | 模糊搜索 |
| limit | int | 默认 30 |

### frank_get_molecule
| 参数 | 类型 | 说明 |
|------|------|------|
| name | str | 分子名/分子式/中文别名 |
| include_xyz | bool | 是否返回 XYZ 坐标 |

### frank_search_pubchem
| 参数 | 类型 | 说明 |
|------|------|------|
| name | str | PubChem 查询名 |
| register | bool | 是否注册到本地库 |

### frank_import_molecule
| 参数 | 类型 | 说明 |
|------|------|------|
| filepath | str | XYZ 文件路径 |
| name | str? | 自定义名称 |
| charge | int | 电荷，默认 0 |
| spin | int | 未配对电子数，默认 0 |

### frank_list_methods
无参数。返回 DFT、post-HF、激发态、多参考、相对论方法列表。

### frank_list_basis_sets
| 参数 | 类型 | 说明 |
|------|------|------|
| category | str? | minimal / split-valence / correlation-consistent 等 |

### frank_recommend_basis
| 参数 | 类型 | 说明 |
|------|------|------|
| method | str | 计算方法 |
| calc_type | str | energy / geometry / frequency / excited / casscf |
| accuracy | str | low / medium / high |
| has_diffuse | bool | 是否需要弥散函数 |

### frank_list_solvents / frank_get_solvent
列出或查询溶剂及溶剂化模型。

## 生成类

### frank_parse_intent
| 参数 | 类型 | 说明 |
|------|------|------|
| query | str | 自然语言请求 |
| use_session | bool | 是否复用会话上下文 |

### frank_generate_code
可用 `query` 自然语言，或用结构化参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| query | str? | 自然语言 |
| molecule | str? | 分子名 |
| method | str? | 如 B3LYP, MP2 |
| basis | str? | 如 6-31g*, cc-pvdz |
| calc_type | str? | energy / geometry / frequency / excited / casscf / nbo / solvation |
| solvent | str? | 溶剂名 |
| n_states | int? | TDDFT 态数 |
| norb, nelec | int? | CASSCF 活性空间 |

### frank_get_help
返回 Frank 完整帮助文本。

## 执行类

### frank_run_calculation
| 参数 | 类型 | 说明 |
|------|------|------|
| query | str | 自然语言请求 |
| interpret | bool | 是否生成结果解读 |
| timeout | int? | 超时秒数 |

### frank_diagnose_error
| 参数 | 类型 | 说明 |
|------|------|------|
| stderr | str | 错误输出 |
| stdout | str | 标准输出 |
| job_context | str? | 计算上下文描述 |

## 工作流类

### frank_plan_workflow
| 参数 | 类型 | 说明 |
|------|------|------|
| query | str | 复杂任务描述 |

### frank_run_workflow
| 参数 | 类型 | 说明 |
|------|------|------|
| workflow_type | str | opt_freq / method_comparison / basis_convergence / pes_scan / solvation |
| molecule | str | 分子名 |
| method | str | 默认 B3LYP |
| basis | str | 默认 6-31g* |
| methods | str? | 逗号分隔，用于 method_comparison |
| basis_sets | str? | 逗号分隔，用于 basis_convergence |
| solvent | str | 默认 water |
| scan_type | str | bond / angle / dihedral |
| atoms | str | 扫描原子索引，如 "0,1" |
| n_points | int | 扫描点数 |
| range_start, range_end | float | 扫描范围 |
| timeout | int? | 超时秒数 |

### frank_run_autonomous
| 参数 | 类型 | 说明 |
|------|------|------|
| query | str | 复杂自然语言任务 |
| timeout | int? | 超时秒数 |

### frank_is_complex_query
| 参数 | 类型 | 说明 |
|------|------|------|
| query | str | 待判断的请求 |

## 知识类

### frank_explain
| 参数 | 类型 | 说明 |
|------|------|------|
| question | str | 计算化学问题 |

### frank_version
返回 Frank 版本信息。

## 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| FRANK_WORK_DIR | 计算工作目录 | 系统临时目录 |
| FRANK_TIMEOUT | 执行超时（秒） | 600 |
