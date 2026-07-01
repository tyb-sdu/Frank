# Frank -- Computational Chemistry Terminal Agent

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![PySCF](https://img.shields.io/badge/PySCF-2.4+-green.svg)](https://pyscf.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Frank is a computational chemistry terminal agent that translates natural language
descriptions into executable quantum chemistry calculations. Describe your molecule
and computational requirements, and Frank generates, executes, diagnoses, and
interprets the results.

**Frank replaces the manual workflow of writing PySCF scripts, debugging convergence
failures, and interpreting raw output -- all through a conversational interface.**

---

## Table of Contents

- [Core Capabilities](#core-capabilities)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
  - [Interactive Mode](#interactive-mode)
  - [Command-Line Mode](#command-line-mode)
  - [Python API](#python-api)
  - [Workflows](#workflows)
- [LLM Integration](#llm-integration)
- [Supported Methods](#supported-methods)
- [Molecule Input](#molecule-input)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Extending Frank](#extending-frank)
- [References](#references)
- [License](#license)

---

## Core Capabilities

| Capability | Description |
|------------|-------------|
| **Code Generation** | Generate executable PySCF Python code from natural language |
| **Direct Execution** | Run calculations and return structured results |
| **Automatic Recovery** | Detect SCF convergence failures, memory issues, linear dependency, and apply recovery strategies automatically |
| **Diagnostics** | Identify basis set mismatches, imaginary frequencies, convergence issues with plain-language explanations |
| **Result Interpretation** | Translate numerical output into chemically meaningful conclusions (HOMO-LUMO gap, polarity, absorption region) |
| **Multi-Step Workflows** | Automate geometry optimization -> frequency validation -> high-accuracy single-point chains |
| **LLM-Powered Parsing** | Use DeepSeek V4 to understand complex natural language queries (optional; keyword fallback always available) |
| **Terminal Visualization** | Plot orbital energy diagrams, UV-Vis spectra, IR spectra, and convergence curves directly in the terminal |

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/frank-chem/frank.git
cd frank
pip install -e .

# Launch interactive mode
frank

# Or run a single calculation
frank run "Calculate the energy of water at B3LYP/6-31G* level"
```

Example session:

```
Frank> calculate the energy of benzene with B3LYP/6-31G*

Parsed intent:
  Molecule: benzene (C6H6)
  Method: B3LYP
  Basis set: 6-31G*
  Calculation type: Single-point energy
  Confidence: 95%

[Generated PySCF code displayed with syntax highlighting]

[OK] Calculation succeeded (duration 3.2 s)

HOMO-LUMO gap: 5.12 eV
  The gap is moderate; the molecule is a semiconductor.
```

---

## Installation

### Requirements

- Python 3.10 or later
- PySCF 2.4 or later
- RDKit (for SMILES and 3D conformer generation)

### Install from source

```bash
git clone https://github.com/frank-chem/frank.git
cd frank
pip install -e .
```

### Install optional dependencies

```bash
# LLM-powered intent parsing (DeepSeek)
pip install openai

# Development and testing
pip install -e ".[dev]"
```

---

## Usage

### Interactive Mode

Launch the interactive REPL:

```bash
frank
```

Interactive features:
- **Command history**: up/down arrow keys navigate previous inputs; persists across sessions
- **Tab completion**: molecule names, methods, basis sets, commands
- **Intent correction**: after parsing, you can edit any parameter before code generation
- **Session state**: Frank remembers your last molecule, method, and basis across queries
- **Onboarding guide**: first-run tutorial with worked examples

Supported inline prefixes:

| Prefix | Action |
|--------|--------|
| `run <query>` | Generate code and execute |
| `search <name>` | Query PubChem |
| `import <file>` | Load XYZ file |
| `compare <mol> <methods>` | Parallel method comparison |
| `converge <mol> <basis_sets>` | Basis set convergence test |
| `batch <mol1,mol2> <method> <basis>` | Multi-molecule calculation |
| `session` | Display current session context |
| `help` | Show full help |
| `quit` | Exit |

### Command-Line Mode

```bash
# Generate code only (no execution)
frank ask "Calculate water energy at B3LYP/6-31G*"

# Generate, execute, and interpret
frank run "Optimize ammonia geometry with MP2/cc-pVDZ"

# With export
frank run "Energy of benzene" --export result.json
frank run "Energy of benzene" --export result.csv --export-format csv

# Display molecule information
frank info h2o
frank info caffeine
frank xyz benzene

# Search PubChem
frank search aspirin
frank search "acetic acid"

# Import XYZ file
frank import molecule.xyz --name mymol --charge 0 --spin 0

# List resources (with pagination)
frank list molecules --page 1 --page-size 20
frank list methods
frank list basis --category correlation-consistent
frank list solvents
frank list aliases
```

### Python API

```python
from frank.agent import FrankAgent

agent = FrankAgent()

# Parse intent and generate code
result = agent.process_request("Calculate water energy at B3LYP/6-31G*")
print(result["script"])           # Generated Python code
print(result["intent"].molecule)  # "h2o"
print(result["intent"].method)    # "B3LYP"

# Execute and get full results
result = agent.run("Energy of benzene with B3LYP/6-31G*")
print(result["execution"].success)
print(result["execution"].duration)
print(result["interpretation"])   # Human-readable interpretation

# Access session state
print(agent.session.last_molecule)
```

### Workflows

Frank supports five multi-step workflow types, each with short aliases:

| Workflow | Alias | Description |
|----------|-------|-------------|
| `opt_freq` | `of` | Geometry optimization -> frequency -> high-accuracy single-point |
| `method_comparison` | `mc`, `compare` | Single-point energy with multiple methods |
| `basis_convergence` | `bc`, `converge` | Energy convergence test across basis sets |
| `pes_scan` | `pes` | Potential energy surface scan along a coordinate |
| `solvation` | `solv` | Gas-phase -> solution-phase free energy |

```bash
# Geometry optimization + frequency
frank workflow of ethanol --method B3LYP --basis 6-31G*

# Method comparison (with alias)
frank workflow mc water --methods HF,B3LYP,MP2,wB97X-D

# Basis set convergence
frank workflow bc benzene --method B3LYP --basis-sets sto-3g,6-31g*,cc-pvdz,cc-pvtz

# PES scan (bond length)
frank workflow pes h2o --scan-type bond --atoms 0,1 --range-start 0.8 --range-end 2.0

# Solvation free energy
frank workflow solv ethanol --solvent water --method B3LYP
```

Workflows display a real-time progress bar with estimated time remaining.

---

## LLM Integration

Frank optionally uses DeepSeek V4 (via OpenAI-compatible API) for natural language
intent parsing. When enabled, Frank can understand complex, ambiguous, or
conversational queries that keyword matching cannot handle.

### Setup

```bash
# Store your API key (never written to source files)
mkdir -p ~/.frank
echo '{"deepseek_api_key": "sk-your-key-here"}' > ~/.frank/config.json
chmod 600 ~/.frank/config.json
```

The API key is read from `~/.frank/config.json` at runtime. It never appears in
source code, environment variables, or command-line arguments.

### Behavior

- **LLM available**: Natural language queries are parsed by DeepSeek with high accuracy
- **LLM unavailable**: Falls back to keyword-based pattern matching (no API key required)
- **Chat responses**: Greetings, questions, and non-chemistry messages receive natural,
  empathetic LLM-generated replies instead of rigid template responses
- **Intent parsing**: LLM extracts molecule, method, basis, calculation type, and
  other parameters from free-form text in either Chinese or English

### Test Connection

```python
from frank.llm import test_connection
ok, msg = test_connection()
print(msg)
```

---

## Supported Methods

### SCF

HF, RHF, UHF, ROHF

### DFT (30+ functionals)

| Category | Examples |
|----------|----------|
| Pure GGA | PBE, BP86, BLYP |
| Hybrid | B3LYP, PBE0, B3PW91 |
| Meta-GGA | M06-L, TPSS |
| Hybrid meta-GGA | M06-2X, M06-HF |
| Range-separated | CAM-B3LYP, wB97X-D, wB97X-V |
| Screened hybrid | HSE06, HSEsol |

### Post-HF

MP2, CCSD, CCSD(T), CISD, FCI, DF-MP2, DF-CCSD

### Excited State

TDDFT, TDA, CIS, ADC(2), EOM-CCSD

### Multi-Reference

CASSCF, CASCI, NEVPT2, CASPT2, DMRG-CASSCF

> Note: PySCF core has no native CASPT2 — Frank generates the equivalent
> intruder-state-free NEVPT2 and states this in the output.

### Solvation

PCM, CPCM, SMD, COSMO — the requested model is honored in the generated code
(e.g. SMD uses `pyscf.solvent.smd.SMD`, PCM/CPCM/COSMO use `solvent.PCM` with the
matching `with_solvent.method`).

> Runnable code generation currently covers: HF/RHF/UHF, all DFT functionals,
> MP2, CCSD, CCSD(T), CISD, FCI, CASSCF, CASCI, NEVPT2 (incl. CASPT2 fallback),
> TDDFT, ADC(2), and EOM-CCSD.

### Relativistic

DKH (0-4), X2C, ECP

---

## Molecule Input

Frank accepts molecules through multiple channels:

1. **Built-in database**: 50+ molecules with pre-optimized 3D coordinates
2. **PubChem lookup**: `frank search <name>` queries PubChem's REST API
3. **SMILES strings**: Direct input like `CCO`, `c1ccccc1`, `CC(=O)O`
4. **XYZ files**: `frank import <file.xyz>`
5. **Natural language**: LLM resolves names like "aspirin", "caffeine", "acetic acid"

---

## Project Structure

```
frank/
├── __init__.py              # Package init, version
├── config.py                # Configuration and API key management
├── agent.py                 # Core agent (intent parsing + code generation)
├── llm.py                   # DeepSeek LLM integration
├── cli/                     # Command-line interfaces
│   ├── main_cli.py          # Synchronous CLI (Click + Rich)
│   ├── async_cli.py         # Asynchronous CLI (real-time streaming)
│   └── completion.py        # Readline tab completion
├── core/                    # Execution pipeline
│   ├── executor.py          # PySCF subprocess execution
│   ├── executor_common.py   # Script enhancement and error classification
│   ├── parser.py            # Output parsing (SCF, MP2, CCSD, TDDFT, etc.)
│   ├── diagnostics.py       # Problem detection and suggestions
│   ├── interpreter.py       # Human-readable result interpretation
│   ├── recovery.py          # Automatic error recovery strategies
│   └── visualizer.py        # Terminal plotting (orbitals, spectra)
├── molecules/               # Molecule management
│   ├── database.py          # Built-in molecule database (50+ entries)
│   ├── sources.py           # External sources (PubChem, XYZ, SMILES)
│   └── utils.py             # SMILES parsing and 3D conformer generation
├── methods/                 # Computational method definitions
│   ├── scf.py               # Hartree-Fock variants
│   ├── dft.py               # DFT functionals (30+ with recommendations)
│   ├── post_hf.py           # MP2, CCSD, CCSD(T)
│   ├── excited.py           # TDDFT, EOM-CCSD
│   ├── casscf.py            # Multi-reference methods
│   ├── solvation.py         # Solvent models and parameters
│   └── relativistic.py      # DKH, X2C, ECP
├── templates/               # Code generation
│   ├── base.py              # Abstract template engine
│   └── pyscf_templates.py   # PySCF concrete implementation
├── basis/                   # Basis set database with recommendations
├── aio/                     # Asynchronous operations
│   ├── agent.py             # Async agent with streaming
│   ├── executor.py          # Async subprocess management
│   └── workflows.py         # Parallel workflow execution
├── workflows/               # Multi-step workflow engine
│   ├── engine.py            # Workflow orchestration
│   └── export.py            # JSON/CSV result export
├── examples/                # Standalone PySCF example scripts
└── tests/                   # Test suite
```

---

## Configuration

Frank stores configuration in `~/.frank/`:

| File | Purpose |
|------|---------|
| `config.json` | API keys, model settings (permissions: 600) |
| `history` | Readline command history |
| `onboarded` | Marker file for first-run detection |

Example `config.json`:

```json
{
  "deepseek_api_key": "sk-...",
  "deepseek_model": "deepseek-chat",
  "deepseek_base_url": "https://api.deepseek.com"
}
```

---

## Extending Frank

### Adding a New Molecule

```python
# In frank/molecules/database.py
_add(Molecule(
    name="my_mol",
    name_cn="My Molecule",
    formula="C2H4",
    smiles="C=C",
    atom_xyz="""
    C  0.000  0.000  0.000
    C  0.000  0.000  1.340
    H  0.000  0.930 -0.590
    H  0.000 -0.930 -0.590
    H  0.000  0.930  1.930
    H  0.000 -0.930  1.930
    """,
    electrons=16,
    tags=["alkene", "planar"],
))
```

### Adding a New DFT Functional

```python
# In frank/methods/dft.py
_register(DFTFunctional(
    name="MYFUNC",
    name_cn="My Functional",
    category="hybrid",
    description="Custom hybrid functional for specific applications",
    when_to_use="Specialized applications",
    accuracy="medium",
))
```

---

## References

- [PySCF Documentation](https://pyscf.org/)
- [PySCF GitHub](https://github.com/pyscf/pyscf)
- [Basis Set Exchange](https://www.basissetexchange.org/)
- [DeepSeek API Documentation](https://platform.deepseek.com/docs)

---

## License

MIT License
