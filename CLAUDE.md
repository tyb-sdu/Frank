# Frank — 计算化学终端智能体

## 项目概述
Frank 是一个计算化学代码生成终端智能体。用户输入分子和计算需求，Frank 生成可直接运行的 Python 代码（基于 PySCF/Psi4）。

## 架构
- `frank/agent.py` — 核心智能体，意图解析 + 代码生成
- `frank/molecules.py` — 分子数据库（常见分子的 3D 坐标）
- `frank/templates/` — 代码模板引擎
- `frank/methods/` — 理论方法实现
- `frank/basis_sets.py` — 基组配置
- `frank/cli.py` — CLI 入口

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
