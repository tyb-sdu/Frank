#!/usr/bin/env python3
"""
Frank -- Computational Chemistry Terminal Agent

Launch interactive mode:
  python run.py

Or use commands:
  python run.py ask "Calculate energy of water at B3LYP/6-31G*"
  python run.py list molecules
  python run.py info h2o
"""

from frank.cli.main_cli import main

if __name__ == "__main__":
    main()
