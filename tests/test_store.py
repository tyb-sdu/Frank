"""Tests for CalcStore (database layer)."""

import os
import tempfile

import pytest


@pytest.fixture
def store_db(monkeypatch):
    """Use isolated SQLite database for each test."""
    from frank.store.database import reset_db_engine, init_db

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    url = f"sqlite:///{path}"
    monkeypatch.setenv("FRANK_DATABASE_URL", url)
    monkeypatch.setenv("FRANK_STORE_ENABLED", "1")
    reset_db_engine()
    init_db()
    yield path
    reset_db_engine()
    try:
        os.unlink(path)
    except OSError:
        pass


class TestJobRepository:
    def test_create_and_get_job(self, store_db):
        from frank.store.repository import JobRepository

        repo = JobRepository()
        job_id = repo.create_job(
            molecule_name="water",
            method="B3LYP",
            basis="6-31g*",
            calc_type="energy",
            query_text="water energy",
            status="running",
        )
        assert job_id

        repo.save_result(job_id, {"energy": -76.0}, execution_success=True)
        job = repo.get_job(job_id)
        assert job["status"] == "completed"
        assert job["molecule"] == "water"
        assert job["energy_hartree"] == -76.0

    def test_list_jobs_filter(self, store_db):
        from frank.store.repository import JobRepository

        repo = JobRepository()
        repo.create_job(molecule_name="water", method="B3LYP", status="completed")
        repo.create_job(molecule_name="benzene", method="MP2", status="pending")

        water_jobs = repo.list_jobs(molecule="water")
        assert len(water_jobs) == 1
        assert water_jobs[0].molecule_name == "water"

    def test_compare_jobs(self, store_db):
        from frank.store.repository import JobRepository

        repo = JobRepository()
        id_a = repo.create_job(molecule_name="water", method="B3LYP", status="running")
        id_b = repo.create_job(molecule_name="water", method="MP2", status="running")
        repo.save_result(id_a, {"energy": -76.0})
        repo.save_result(id_b, {"energy": -75.5})

        result = repo.compare_jobs(id_a, id_b)
        assert result["delta"]["energy_hartree"] == pytest.approx(0.5)

    def test_export_csv(self, store_db):
        from frank.store.repository import JobRepository

        repo = JobRepository()
        job_id = repo.create_job(molecule_name="water", method="B3LYP", status="running")
        repo.save_result(job_id, {"energy": -76.0})

        csv = repo.export_csv()
        assert "water" in csv
        assert "B3LYP" in csv

    def test_workflow(self, store_db):
        from frank.store.repository import JobRepository

        repo = JobRepository()
        wf_id = repo.create_workflow(
            title="Test reaction",
            workflow_type="reaction_thermo",
            plan_json={"tasks": []},
        )
        job_id = repo.create_job(molecule_name="h2", method="B3LYP", status="pending")
        repo.link_workflow_job(wf_id, job_id, 0)

        wf = repo.get_workflow(wf_id)
        assert wf["title"] == "Test reaction"
        assert len(wf["steps"]) == 1
        assert wf["steps"][0]["molecule"] == "h2"


class TestPersist:
    def test_create_job_for_run(self, store_db):
        from frank.store.persist import create_job_for_run, persist_execution_to_store
        from frank.core.executor import ExecutionResult

        job_id = create_job_for_run(
            molecule_name="water",
            method="B3LYP",
            basis="6-31g*",
            calc_type="energy",
            force=True,
        )
        assert job_id

        execution = ExecutionResult(
            success=True,
            return_code=0,
            stdout="",
            stderr="",
            duration=1.5,
            extracted_results={"energy": -76.0},
        )
        persist_execution_to_store(job_id, execution, force=True)

        from frank.store.repository import JobRepository
        job = JobRepository().get_job(job_id)
        assert job["status"] == "completed"
        assert job["energy_hartree"] == -76.0
