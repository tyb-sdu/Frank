from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Molecule:
    name: str
    name_cn: str
    formula: str
    smiles: str
    atom_xyz: str
    charge: int = 0
    spin: int = 0
    symmetry: str = "C1"
    tags: list[str] = field(default_factory=list)
    electrons: Optional[int] = None

    @property
    def multiplicity(self) -> int:
        return self.spin + 1

    @property
    def atom_count(self) -> int:
        return len([line for line in self.atom_xyz.strip().split('\n') if line.strip()])


MOLECULES: dict[str, Molecule] = {}


def _add(mol: Molecule):
    MOLECULES[mol.name] = mol
    if mol.name_cn != mol.name:
        MOLECULES[mol.name_cn] = mol
    if mol.formula not in MOLECULES:
        MOLECULES[mol.formula] = mol


_add(Molecule(
    name="h2", name_cn="氢气", formula="H2", smiles="[H][H]",
    atom_xyz="""
    H  0.000  0.000  0.000
    H  0.000  0.000  0.741
    """,
    electrons=2, tags=["diatomic", "homonuclear"],
))

_add(Molecule(
    name="hf", name_cn="氟化氢", formula="HF", smiles="F",
    atom_xyz="""
    H  0.000  0.000  0.000
    F  0.000  0.000  0.917
    """,
    electrons=10, tags=["diatomic", "heteronuclear"],
))

_add(Molecule(
    name="hcl", name_cn="氯化氢", formula="HCl", smiles="Cl",
    atom_xyz="""
    H  0.000  0.000  0.000
    Cl 0.000  0.000  1.275
    """,
    electrons=18, tags=["diatomic", "heteronuclear"],
))

_add(Molecule(
    name="n2", name_cn="氮气", formula="N2", smiles="N#N",
    atom_xyz="""
    N  0.000  0.000  0.000
    N  0.000  0.000  1.098
    """,
    electrons=14, tags=["diatomic", "homonuclear"],
))

_add(Molecule(
    name="o2", name_cn="氧气", formula="O2", smiles="O=O",
    atom_xyz="""
    O  0.000  0.000  0.000
    O  0.000  0.000  1.208
    """,
    electrons=16, spin=2, tags=["diatomic", "homonuclear", "radical"],
))

_add(Molecule(
    name="co", name_cn="一氧化碳", formula="CO", smiles="[C-]#[O+]",
    atom_xyz="""
    C  0.000  0.000  0.000
    O  0.000  0.000  1.128
    """,
    electrons=14, tags=["diatomic", "heteronuclear"],
))

_add(Molecule(
    name="cl2", name_cn="氯气", formula="Cl2", smiles="ClCl",
    atom_xyz="""
    Cl 0.000  0.000  0.000
    Cl 0.000  0.000  1.988
    """,
    electrons=34, tags=["diatomic", "homonuclear"],
))

_add(Molecule(
    name="h2o", name_cn="水", formula="H2O", smiles="O",
    atom_xyz="""
    O  0.000  0.000  0.117
    H  0.000  0.757 -0.469
    H  0.000 -0.757 -0.469
    """,
    symmetry="C2v", electrons=10, tags=["triatomic", "bent", "polar"],
))

_add(Molecule(
    name="co2", name_cn="二氧化碳", formula="CO2", smiles="O=C=O",
    atom_xyz="""
    C  0.000  0.000  0.000
    O  0.000  0.000  1.162
    O  0.000  0.000 -1.162
    """,
    symmetry="Dinfh", electrons=22, tags=["triatomic", "linear"],
))

_add(Molecule(
    name="h2s", name_cn="硫化氢", formula="H2S", smiles="S",
    atom_xyz="""
    S  0.000  0.000  0.103
    H  0.000  0.962 -0.411
    H  0.000 -0.962 -0.411
    """,
    symmetry="C2v", electrons=18, tags=["triatomic", "bent"],
))

_add(Molecule(
    name="so2", name_cn="二氧化硫", formula="SO2", smiles="O=S=O",
    atom_xyz="""
    S  0.000  0.000  0.371
    O  0.000  1.107 -0.371
    O  0.000 -1.107 -0.371
    """,
    symmetry="C2v", electrons=32, tags=["triatomic", "bent"],
))

_add(Molecule(
    name="o3", name_cn="臭氧", formula="O3", smiles="[O-][O+]=O",
    atom_xyz="""
    O  0.000  0.000  0.431
    O  0.000  1.097 -0.216
    O  0.000 -1.097 -0.216
    """,
    symmetry="C2v", electrons=24, tags=["triatomic", "bent"],
))

_add(Molecule(
    name="no2", name_cn="二氧化氮", formula="NO2", smiles="[O]N=O",
    atom_xyz="""
    N  0.000  0.000  0.371
    O  0.000  1.107 -0.185
    O  0.000 -1.107 -0.185
    """,
    symmetry="C2v", electrons=23, spin=1, tags=["triatomic", "bent", "radical"],
))

_add(Molecule(
    name="hcn", name_cn="氰化氢", formula="HCN", smiles="C#N",
    atom_xyz="""
    H  0.000  0.000 -1.065
    C  0.000  0.000  0.000
    N  0.000  0.000  1.156
    """,
    symmetry="Cinfv", electrons=14, tags=["triatomic", "linear"],
))

_add(Molecule(
    name="h2co", name_cn="甲醛", formula="H2CO", smiles="C=O",
    atom_xyz="""
    C  0.000  0.000  0.000
    O  0.000  0.000  1.203
    H  0.000  0.934 -0.587
    H  0.000 -0.934 -0.587
    """,
    symmetry="C2v", electrons=16, tags=["triatomic", "carbonyl"],
))

_add(Molecule(
    name="nh3", name_cn="氨", formula="NH3", smiles="N",
    atom_xyz="""
    N  0.000  0.000  0.116
    H  0.000  0.939 -0.271
    H  0.813 -0.470 -0.271
    H -0.813 -0.470 -0.271
    """,
    symmetry="C3v", electrons=10, tags=["pyramidal", "polar"],
))

_add(Molecule(
    name="bf3", name_cn="三氟化硼", formula="BF3", smiles="B(F)(F)F",
    atom_xyz="""
    B  0.000  0.000  0.000
    F  0.000  1.307  0.000
    F  1.132 -0.654  0.000
    F -1.132 -0.654  0.000
    """,
    symmetry="D3h", electrons=48, tags=["planar", "trigonal"],
))

_add(Molecule(
    name="ch2o", name_cn="甲醛", formula="CH2O", smiles="C=O",
    atom_xyz="""
    C  0.000  0.000  0.000
    O  0.000  0.000  1.203
    H  0.000  0.934 -0.587
    H  0.000 -0.934 -0.587
    """,
    symmetry="C2v", electrons=16, tags=["carbonyl", "planar"],
))

_add(Molecule(
    name="ch4", name_cn="甲烷", formula="CH4", smiles="C",
    atom_xyz="""
    C  0.000  0.000  0.000
    H  0.629  0.629  0.629
    H -0.629 -0.629  0.629
    H -0.629  0.629 -0.629
    H  0.629 -0.629 -0.629
    """,
    symmetry="Td", electrons=10, tags=["tetrahedral"],
))

_add(Molecule(
    name="ch3f", name_cn="氟甲烷", formula="CH3F", smiles="CF",
    atom_xyz="""
    C  0.000  0.000  0.000
    F  0.000  0.000  1.383
    H  1.027  0.000 -0.364
    H -0.514  0.889 -0.364
    H -0.514 -0.889 -0.364
    """,
    symmetry="C3v", electrons=18, tags=["halomethane"],
))

_add(Molecule(
    name="ch3cl", name_cn="氯甲烷", formula="CH3Cl", smiles="CCl",
    atom_xyz="""
    C  0.000  0.000  0.000
    Cl 0.000  0.000  1.781
    H  1.031  0.000 -0.375
    H -0.516  0.893 -0.375
    H -0.516 -0.893 -0.375
    """,
    symmetry="C3v", electrons=26, tags=["halomethane"],
))

_add(Molecule(
    name="ch3oh", name_cn="甲醇", formula="CH3OH", smiles="CO",
    atom_xyz="""
    C  -0.046  0.000 -0.073
    O  -0.046  0.000  1.381
    H   0.031  0.940 -0.490
    H   0.031 -0.470 -0.490
    H   0.031 -0.470 -0.490
    H  -0.046  0.000  1.889
    """,
    electrons=18, tags=["alcohol"],
))

_add(Molecule(
    name="nh4+", name_cn="铵离子", formula="NH4+", smiles="[NH4+]",
    atom_xyz="""
    N  0.000  0.000  0.000
    H  0.629  0.629  0.629
    H -0.629 -0.629  0.629
    H -0.629  0.629 -0.629
    H  0.629 -0.629 -0.629
    """,
    charge=1, symmetry="Td", electrons=10, tags=["ion", "cation"],
))

_add(Molecule(
    name="ph3", name_cn="膦", formula="PH3", smiles="P",
    atom_xyz="""
    P  0.000  0.000  0.116
    H  0.000  1.085 -0.315
    H  0.940 -0.543 -0.315
    H -0.940 -0.543 -0.315
    """,
    symmetry="C3v", electrons=18, tags=["pyramidal"],
))

_add(Molecule(
    name="c2h4", name_cn="乙烯", formula="C2H4", smiles="C=C",
    atom_xyz="""
    C  0.000  0.000  0.000
    C  0.000  0.000  1.339
    H  0.000  0.929 -0.587
    H  0.000 -0.929 -0.587
    H  0.000  0.929  1.926
    H  0.000 -0.929  1.926
    """,
    symmetry="D2h", electrons=16, tags=["alkene", "planar"],
))

_add(Molecule(
    name="c2h2", name_cn="乙炔", formula="C2H2", smiles="C#C",
    atom_xyz="""
    H  0.000  0.000 -1.662
    C  0.000  0.000 -0.605
    C  0.000  0.000  0.605
    H  0.000  0.000  1.662
    """,
    symmetry="Dinfh", electrons=14, tags=["alkyne", "linear"],
))

_add(Molecule(
    name="h2o2", name_cn="过氧化氢", formula="H2O2", smiles="OO",
    atom_xyz="""
    O  0.000  0.000  0.000
    O  0.000  0.000  1.475
    H  0.000  0.949 -0.415
    H  0.000 -0.949  1.890
    """,
    electrons=18, tags=["peroxide"],
))

_add(Molecule(
    name="ch3nh2", name_cn="甲胺", formula="CH3NH2", smiles="CN",
    atom_xyz="""
    C  -0.046  0.000  0.000
    N  -0.046  0.000  1.471
    H   0.894  0.000 -0.534
    H  -0.516  0.889 -0.534
    H  -0.516 -0.889 -0.534
    H   0.318  0.853  1.879
    H   0.318 -0.853  1.879
    """,
    electrons=18, tags=["amine"],
))

_add(Molecule(
    name="hno3", name_cn="硝酸", formula="HNO3", smiles="O[N+](=O)[O-]",
    atom_xyz="""
    N  0.000  0.000  0.000
    O  0.000  0.000  1.210
    O  1.099  0.000 -0.520
    O -1.099  0.000 -0.520
    H  1.590  0.000  0.270
    """,
    electrons=32, tags=["acid", "nitrogen"],
))

_add(Molecule(
    name="c2h6", name_cn="乙烷", formula="C2H6", smiles="CC",
    atom_xyz="""
    C  0.000  0.000  0.762
    C  0.000  0.000 -0.762
    H  0.000  1.020  1.157
    H  0.883 -0.510  1.157
    H -0.883 -0.510  1.157
    H  0.000 -1.020 -1.157
    H  0.000  1.020 -1.157
    """,
    electrons=18, tags=["alkane"],
))

_add(Molecule(
    name="ch3cho", name_cn="乙醛", formula="CH3CHO", smiles="CC=O",
    atom_xyz="""
    C  0.000  0.000  0.000
    C  0.000  0.000  1.509
    O  0.000  0.000  2.670
    H  1.022  0.000 -0.544
    H -0.511  0.886 -0.544
    H -0.511 -0.886 -0.544
    H  0.000  0.000 -0.544
    """,
    electrons=24, tags=["aldehyde", "carbonyl"],
))

_add(Molecule(
    name="ch3cooh", name_cn="乙酸", formula="CH3COOH", smiles="CC(=O)O",
    atom_xyz="""
    C  -0.046  0.000 -0.073
    C  -0.046  0.000  1.509
    O  -0.046  0.000  2.070
    O  -0.046  0.000 -0.644
    H   0.894  0.000 -0.534
    H  -0.516  0.889 -0.534
    H  -0.516 -0.889 -0.534
    H  -0.046  0.000  2.110
    """,
    electrons=32, tags=["carboxylic_acid"],
))

_add(Molecule(
    name="ch3ch2oh", name_cn="乙醇", formula="CH3CH2OH", smiles="CCO",
    atom_xyz="""
    C   0.000  0.000  0.000
    C   0.000  0.000  1.509
    O   0.000  0.000  2.200
    H   1.022  0.000 -0.544
    H  -0.511  0.886 -0.544
    H  -0.511 -0.886 -0.544
    H   0.000  0.000  2.600
    """,
    electrons=26, tags=["alcohol"],
))

_add(Molecule(
    name="c2h5cl", name_cn="氯乙烷", formula="C2H5Cl", smiles="CCCl",
    atom_xyz="""
    C  0.000  0.000  0.000
    C  0.000  0.000  1.509
    Cl 0.000  0.000  2.750
    H  1.022  0.000 -0.544
    H -0.511  0.886 -0.544
    H -0.511 -0.886 -0.544
    H  0.000  0.000 -0.544
    """,
    electrons=34, tags=["haloalkane"],
))

_add(Molecule(
    name="c3h8", name_cn="丙烷", formula="C3H8", smiles="CCC",
    atom_xyz="""
    C  0.000  0.000  0.000
    C  0.000  0.000  1.509
    C  0.000  0.000  3.018
    H  1.022  0.000 -0.544
    H -0.511  0.886 -0.544
    H -0.511 -0.886 -0.544
    H  1.022  0.000  3.562
    H -0.511  0.886  3.562
    H -0.511 -0.886  3.562
    """,
    electrons=26, tags=["alkane"],
))

_add(Molecule(
    name="c3h6", name_cn="环丙烷", formula="C3H6", smiles="C1CC1",
    atom_xyz="""
    C  0.000  0.000  0.000
    C  1.260  0.727  0.000
    C  1.260 -0.727  0.000
    H -0.940  0.000  0.000
    H  1.890  1.260  0.000
    H  1.890 -1.260  0.000
    """,
    electrons=24, tags=["cycloalkane"],
))

_add(Molecule(
    name="ch2cl2", name_cn="二氯甲烷", formula="CH2Cl2", smiles="C(Cl)Cl",
    atom_xyz="""
    C  0.000  0.000  0.000
    Cl 1.540  0.000  0.000
    Cl -1.540  0.000  0.000
    H  0.000  1.040  0.000
    H  0.000 -1.040  0.000
    """,
    electrons=42, tags=["halomethane"],
))

_add(Molecule(
    name="chcl3", name_cn="氯仿", formula="CHCl3", smiles="C(Cl)(Cl)Cl",
    atom_xyz="""
    C  0.000  0.000  0.000
    Cl 1.540  0.000  0.000
    Cl -0.770  1.334  0.000
    Cl -0.770 -1.334  0.000
    H  0.000  0.000  1.070
    """,
    electrons=58, tags=["halomethane"],
))

_add(Molecule(
    name="ccl4", name_cn="四氯化碳", formula="CCl4", smiles="C(Cl)(Cl)(Cl)Cl",
    atom_xyz="""
    C  0.000  0.000  0.000
    Cl 1.540  0.000  0.000
    Cl -1.540  0.000  0.000
    Cl 0.000  1.540  0.000
    Cl 0.000 -1.540  0.000
    """,
    electrons=74, symmetry="Td", tags=["halomethane"],
))

_add(Molecule(
    name="c6h6", name_cn="苯", formula="C6H6", smiles="c1ccccc1",
    atom_xyz="""
    C  0.000  1.396  0.000
    C  1.209  0.698  0.000
    C  1.209 -0.698  0.000
    C  0.000 -1.396  0.000
    C -1.209 -0.698  0.000
    C -1.209  0.698  0.000
    H  0.000  2.479  0.000
    H  2.147  1.240  0.000
    H  2.147 -1.240  0.000
    H  0.000 -2.479  0.000
    H -2.147 -1.240  0.000
    H -2.147  1.240  0.000
    """,
    symmetry="D6h", electrons=42, tags=["aromatic", "planar", "ring"],
))

_add(Molecule(
    name="c5h5n", name_cn="吡啶", formula="C5H5N", smiles="c1ccncc1",
    atom_xyz="""
    N  0.000  1.340  0.000
    C  1.166  0.670  0.000
    C  1.166 -0.670  0.000
    C  0.000 -1.340  0.000
    C -1.166 -0.670  0.000
    C -1.166  0.670  0.000
    H  2.080  1.240  0.000
    H  2.080 -1.240  0.000
    H  0.000 -2.479  0.000
    H -2.080 -1.240  0.000
    H -2.080  1.240  0.000
    """,
    symmetry="C2v", electrons=42, tags=["heterocycle", "aromatic"],
))

_add(Molecule(
    name="ch3coch3", name_cn="丙酮", formula="CH3COCH3", smiles="CC(=O)C",
    atom_xyz="""
    C  0.000  0.000  0.000
    C  0.000  0.000  1.509
    C  0.000  0.000  3.018
    O  0.000  0.000  2.070
    H  1.022  0.000 -0.544
    H -0.511  0.886 -0.544
    H -0.511 -0.886 -0.544
    H  1.022  0.000  3.562
    H -0.511  0.886  3.562
    H -0.511 -0.886  3.562
    """,
    electrons=32, tags=["ketone", "carbonyl"],
))

_add(Molecule(
    name="h3o+", name_cn="水合氢离子", formula="H3O+", smiles="[OH3+]",
    atom_xyz="""
    O  0.000  0.000  0.116
    H  0.000  0.939 -0.271
    H  0.813 -0.470 -0.271
    H -0.813 -0.470 -0.271
    """,
    charge=1, symmetry="C3v", electrons=10, tags=["ion", "cation"],
))

_add(Molecule(
    name="oh-", name_cn="氢氧根", formula="OH-", smiles="[OH-]",
    atom_xyz="""
    O  0.000  0.000  0.000
    H  0.000  0.000  0.969
    """,
    charge=-1, electrons=10, tags=["ion", "anion"],
))

_add(Molecule(
    name="ch3", name_cn="甲基自由基", formula="CH3", smiles="[CH3]",
    atom_xyz="""
    C  0.000  0.000  0.000
    H  0.000  1.078  0.000
    H  0.934 -0.539  0.000
    H -0.934 -0.539  0.000
    """,
    spin=1, symmetry="D3h", electrons=9, tags=["radical", "planar"],
))

_add(Molecule(
    name="ch2", name_cn="亚甲基", formula="CH2", smiles="[CH2]",
    atom_xyz="""
    C  0.000  0.000  0.000
    H  0.000  0.934 -0.333
    H  0.000 -0.934 -0.333
    """,
    spin=1, electrons=8, tags=["radical", "carbene"],
))

_add(Molecule(
    name="no", name_cn="一氧化氮", formula="NO", smiles="[N]=O",
    atom_xyz="""
    N  0.000  0.000  0.000
    O  0.000  0.000  1.152
    """,
    spin=1, electrons=15, tags=["radical", "diatomic"],
))

_add(Molecule(
    name="c2h5oh", name_cn="乙醇", formula="C2H5OH", smiles="CCO",
    atom_xyz="""
    C  0.000  0.000  0.000
    C  0.000  0.000  1.509
    O  0.000  0.000  2.200
    H  1.022  0.000 -0.544
    H -0.511  0.886 -0.544
    H -0.511 -0.886 -0.544
    H  0.000  0.000 -0.544
    H  0.000  0.000  2.600
    """,
    electrons=26, tags=["alcohol"],
))

_add(Molecule(
    name="hcooh", name_cn="甲酸", formula="HCOOH", smiles="C(=O)O",
    atom_xyz="""
    C  0.000  0.000  0.000
    O  0.000  0.000  1.210
    O  1.099  0.000 -0.520
    H  0.000  0.000 -0.544
    H  1.590  0.000  0.270
    """,
    electrons=24, tags=["carboxylic_acid"],
))

_add(Molecule(
    name="ch3och3", name_cn="二甲醚", formula="CH3OCH3", smiles="COC",
    atom_xyz="""
    C  0.000  0.000  0.000
    O  0.000  0.000  1.410
    C  0.000  0.000  2.820
    H  1.022  0.000 -0.544
    H -0.511  0.886 -0.544
    H -0.511 -0.886 -0.544
    H  1.022  0.000  3.364
    H -0.511  0.886  3.364
    H -0.511 -0.886  3.364
    """,
    electrons=26, tags=["ether"],
))

_add(Molecule(
    name="cyclohexane", name_cn="环己烷", formula="C6H12", smiles="C1CCCCC1",
    atom_xyz="""
    C  1.250  0.722  0.250
    C  1.250 -0.722 -0.250
    C  0.000 -1.443  0.250
    C -1.250 -0.722 -0.250
    C -1.250  0.722  0.250
    C  0.000  1.443 -0.250
    H  2.150  1.250  0.500
    H  2.150 -1.250 -0.500
    H  0.000 -2.500  0.500
    H -2.150 -1.250 -0.500
    H -2.150  1.250  0.500
    H  0.000  2.500 -0.500
    """,
    electrons=54, tags=["cycloalkane"],
))

# Ions and tautomers (Aitomia benchmark support)
_add(Molecule(
    name="h+", name_cn="质子", formula="H+", smiles="[H+]",
    atom_xyz="H  0.000  0.000  0.000",
    charge=1, spin=0, electrons=0, tags=["ion", "cation"],
))

_add(Molecule(
    name="ethenol", name_cn="乙烯醇(烯醇式乙醛)", formula="C2H4O", smiles="C=C(O)",
    atom_xyz="""
    C  0.000  0.000  0.000
    C  0.000  0.000  1.340
    O  0.000  1.120  1.890
    H  0.000  0.929 -0.587
    H  0.000 -0.929 -0.587
    H  0.000 -0.929  1.890
    H  0.000  1.120  2.850
    """,
    electrons=24, tags=["tautomer", "enol"],
))

_add(Molecule(
    name="propen2ol", name_cn="丙烯-2-醇(烯醇式丙酮)", formula="C3H6O", smiles="CC(=C)O",
    atom_xyz="""
    C  0.000  0.000  0.000
    C  1.520  0.000  0.000
    C  2.080  1.220  0.000
    O  2.080 -1.120  0.000
    H -0.370  0.510 -0.890
    H -0.370  0.510  0.890
    H -0.370 -1.020  0.000
    H  3.160  1.220  0.000
    H  2.080 -1.880  0.660
    """,
    electrons=32, tags=["tautomer", "enol"],
))

_add(Molecule(
    name="butadiene", name_cn="1,3-丁二烯", formula="C4H6", smiles="C=CC=C",
    atom_xyz="""
    C  0.000  0.000  0.000
    C  1.340  0.000  0.000
    C  2.030  1.210  0.000
    C  3.370  1.210  0.000
    H -0.370  0.510 -0.890
    H -0.370  0.510  0.890
    H  1.710 -0.510 -0.890
    H  1.710 -0.510  0.890
    H  3.740  0.700  0.890
    H  3.740  1.720 -0.890
    """,
    electrons=30, tags=["conjugation", "alkene"],
))

_add(Molecule(
    name="hexatriene", name_cn="1,3,5-己三烯", formula="C6H8", smiles="C=CC=CC=C",
    atom_xyz="""
    C  0.000  0.000  0.000
    C  1.340  0.000  0.000
    C  2.030  1.210  0.000
    C  3.370  1.210  0.000
    C  4.060  0.000  0.000
    C  5.400  0.000  0.000
    H -0.370  0.510 -0.890
    H -0.370  0.510  0.890
    H  1.710 -0.510 -0.890
    H  1.710 -0.510  0.890
    H  3.740  1.720  0.890
    H  3.740  1.720 -0.890
    H  4.430 -0.510 -0.890
    H  5.770  0.510  0.890
    """,
    electrons=42, tags=["conjugation", "alkene"],
))

_add(Molecule(
    name="aniline", name_cn="苯胺", formula="C6H7N", smiles="Nc1ccccc1",
    atom_xyz="""
    N  0.000  0.000  0.000
    C  1.400  0.000  0.000
    C  2.100  1.210  0.000
    C  3.500  1.210  0.000
    C  4.200  0.000  0.000
    C  3.500 -1.210  0.000
    C  2.100 -1.210  0.000
    H -0.360  0.510 -0.890
    H -0.360  0.510  0.890
    H  1.560  2.150  0.000
    H  4.040  2.150  0.000
    H  5.290  0.000  0.000
    H  4.040 -2.150  0.000
    H  1.560 -2.150  0.000
    """,
    electrons=52, tags=["aromatic", "amine"],
))

# Common name aliases
MOLECULE_ALIASES: dict[str, str] = {
    "acetaldehyde": "ch3cho",
    "乙醛": "ch3cho",
    "acetone": "ch3coch3",
    "丙酮": "ch3coch3",
    "water": "h2o",
    "水": "h2o",
    "ammonia": "nh3",
    "氨": "nh3",
    "benzene": "c6h6",
    "苯": "c6h6",
    "ethene": "c2h4",
    "乙烯": "c2h4",
    "ethanol": "ch3ch2oh",
    "乙醇": "ch3ch2oh",
    "methanol": "ch3oh",
    "甲醇": "ch3oh",
}


def get_molecule(name: str) -> Molecule:
    if name in MOLECULES:
        return MOLECULES[name]
    name_lower = name.lower()
    if name_lower in MOLECULES:
        return MOLECULES[name_lower]
    if name_lower in MOLECULE_ALIASES:
        return MOLECULES[MOLECULE_ALIASES[name_lower]]
    if name in MOLECULE_ALIASES:
        return MOLECULES[MOLECULE_ALIASES[name]]
    name_no_space = name.replace(" ", "").replace("_", "")
    if name_no_space in MOLECULES:
        return MOLECULES[name_no_space]
    if name_lower.replace(" ", "") in MOLECULES:
        return MOLECULES[name_lower.replace(" ", "")]
    from .sources import resolve_molecule, register_molecule
    mol = resolve_molecule(name)
    if mol:
        register_molecule(mol)
        return mol

    # Fuzzy matching fallback
    import difflib
    all_names = list(MOLECULES.keys())
    suggestions = difflib.get_close_matches(name, all_names, n=3, cutoff=0.4)
    msg = f"Molecule '{name}' not found."
    if suggestions:
        msg += f" Did you mean: {', '.join(suggestions)}?"
    msg += " Use 'search <name>' to query PubChem, or 'list molecules' to see available entries."
    raise KeyError(msg)


def list_molecules(tag: Optional[str] = None) -> list[Molecule]:
    seen = set()
    result = []
    for mol in MOLECULES.values():
        if mol.name not in seen:
            seen.add(mol.name)
            if tag is None or tag in mol.tags:
                result.append(mol)
    return sorted(result, key=lambda m: m.electrons or 0)


def list_tags() -> list[str]:
    tags = set()
    for mol in MOLECULES.values():
        tags.update(mol.tags)
    return sorted(tags)


def search_molecules(query: str) -> list[Molecule]:
    query_lower = query.lower()
    results = []
    seen = set()
    for mol in MOLECULES.values():
        if mol.name in seen:
            continue
        if (query_lower in mol.name or
            query_lower in mol.name_cn or
            query_lower in mol.formula.lower() or
            query_lower in mol.smiles.lower() or
            any(query_lower in tag for tag in mol.tags)):
            results.append(mol)
            seen.add(mol.name)
    return results


def get_xyz_block(mol: Molecule) -> str:
    lines = [line.strip() for line in mol.atom_xyz.strip().split('\n') if line.strip()]
    xyz = f"{len(lines)}\n"
    xyz += f"{mol.name_cn} ({mol.formula})\n"
    for line in lines:
        xyz += line + "\n"
    return xyz


def get_pyscf_geometry(mol: Molecule) -> str:
    lines = []
    for line in mol.atom_xyz.strip().split('\n'):
        line = line.strip()
        if line:
            lines.append(line)
    return '\n'.join(lines)
