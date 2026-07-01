# Frank — 计算化学终端智能体

## 项目概述
Frank 是一个计算化学代码生成终端智能体。用户输入分子和计算需求，Frank 生成可直接运行的 Python 代码（基于 PySCF）。

## 架构
- `frank/agent.py` — 核心智能体，意图解析 + 代码生成
- `frank/molecules/` — 分子数据库（`database.py` 内置坐标、`sources.py` PubChem/XYZ/SMILES、`utils.py`、`conformers.py`、`validation.py`）
- `frank/templates/` — 代码模板引擎（`pyscf_templates.py` 为主引擎）
- `frank/methods/` — 理论方法元数据（scf/dft/post_hf/excited/casscf/solvation/relativistic）
- `frank/basis/` — 基组配置
- `frank/cli/` — CLI 入口（`main_cli.py` 为 `frank` 命令）
- `frank/core/` — 执行管线（executor/parser/diagnostics/interpreter/recovery/cost_estimator + backends）
- `frank/mcp/` — MCP Server（20 个工具，`frank-mcp` 命令）
- `frank/graph/` — LangGraph 编排（可选）
- `frank/orchestrator/` — 多步自主工作流编排
- `frank/workflows/` — 预定义多步工作流引擎
- `frank/store/` + `frank/queue/` — 作业持久化（SQLAlchemy）与 Celery/Redis 后台队列（可选）
- `frank/knowledge/` — 知识库问答（RAG-lite）

## 技术栈
- Python 3.10+
- PySCF（主要后端）
- RDKit（分子处理）
- Rich（终端美化）

## 开发约定
- 所有代码模板使用 f-string 或 Jinja2
- 分子坐标使用标准 XYZ 格式
- 输出代码必须可直接复制运行
- 中文注释，英文代码
