"""Tests for Aitomia-inspired stoichiometry, validation, and error diagnosis."""

import pytest
from frank.molecules.database import get_molecule
from frank.orchestrator.stoichiometry import (
    solve_stoichiometry,
    format_energy_delta,
    count_elements,
)
from frank.molecules.validation import validate_structure, _parse_formula
from frank.core.error_diagnosis import diagnose_failure, format_diagnosis


class TestStoichiometry:
    def test_water_formation(self):
        result = solve_stoichiometry(["h2", "o2"], ["h2o"])
        assert result.balanced
        assert ("h2", 2) in result.reactants
        assert ("o2", 1) in result.reactants
        assert ("h2o", 2) in result.products

    def test_unbalanced_reaction(self):
        result = solve_stoichiometry(["h2"], ["h2o"])
        assert not result.balanced
        assert result.error

    def test_format_energy_delta(self):
        text = format_energy_delta(-0.05)
        assert "Ha" in text
        assert "kcal/mol" in text

    def test_count_elements(self):
        mol = get_molecule("h2o")
        counts = count_elements(mol)
        assert counts["H"] == 2
        assert counts["O"] == 1


class TestValidation:
    def test_parse_formula(self):
        counts = _parse_formula("C6H6")
        assert counts["C"] == 6
        assert counts["H"] == 6

    def test_validate_h2o(self):
        mol = get_molecule("h2o")
        result = validate_structure(mol)
        assert result.valid

    def test_validate_mismatch(self):
        mol = get_molecule("h2o")
        result = validate_structure(mol, expected_formula="CH4")
        assert not result.valid


class TestErrorDiagnosis:
    def test_rule_based_scf(self):
        diag = diagnose_failure(
            stderr="SCF not converged after max cycle reached",
            stdout="",
        )
        assert diag.likely_cause
        assert len(diag.suggestions) >= 1

    def test_format_diagnosis(self):
        from frank.core.error_diagnosis import ErrorDiagnosis
        text = format_diagnosis(ErrorDiagnosis(
            likely_cause="SCF did not converge",
            suggestions=["Increase max_cycle"],
        ))
        assert "SCF" in text
        assert "Increase max_cycle" in text
