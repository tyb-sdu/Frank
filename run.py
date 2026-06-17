#!/usr/bin/env python3
"""
Frank — 计算化学终端智能体

直接运行此文件启动交互模式:
  python run.py

或使用命令:
  python run.py ask "计算水分子的 B3LYP 能量"
  python run.py list molecules
  python run.py info h2o
"""

from frank.cli import main

if __name__ == "__main__":
    main()
