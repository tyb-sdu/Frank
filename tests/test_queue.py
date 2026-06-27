"""Tests for MolQueue (Celery task layer)."""

import os
import tempfile

import pytest


@pytest.fixture
def store_and_eager_celery(monkeypatch):
    from frank.store.database import reset_db_engine, init_db
    from frank.queue.celery_app import celery_app

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setenv("FRANK_DATABASE_URL", f"sqlite:///{path}")
    monkeypatch.setenv("FRANK_STORE_ENABLED", "1")
    reset_db_engine()
    init_db()

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield celery_app
    reset_db_engine()
    celery_app.conf.task_always_eager = False
    try:
        os.unlink(path)
    except OSError:
        pass


class TestCeleryTasks:
    def test_run_pyscf_job_eager(self, store_and_eager_celery, monkeypatch):
        from frank.store.repository import JobRepository
        from frank.queue.tasks import run_pyscf_job
        from frank.core.executor import ExecutionResult

        repo = JobRepository()
        job_id = repo.create_job(
            molecule_name="water",
            method="HF",
            status="pending",
        )

        fake_result = ExecutionResult(
            success=True,
            return_code=0,
            stdout="_FRANK_RESULT_JSON:{\"energy\": -76.0}",
            stderr="",
            duration=2.0,
            output_dir="/tmp/test",
            extracted_results={"energy": -76.0},
        )

        monkeypatch.setattr(
            "frank.core.executor.PySCFExecutor.execute_with_recovery",
            lambda self, script, job_name, original_basis=None: (fake_result, []),
        )

        result = run_pyscf_job(job_id, "print('test')", "water_hf")
        assert result["success"] is True

        job = repo.get_job(job_id)
        assert job["status"] == "completed"
        assert job["energy_hartree"] == -76.0

    def test_submit_single_job(self, store_and_eager_celery, monkeypatch):
        from frank.store.repository import JobRepository
        from frank.queue.tasks import submit_single_job
        from frank.core.executor import ExecutionResult

        fake_result = ExecutionResult(
            success=True,
            return_code=0,
            stdout="",
            stderr="",
            duration=1.0,
            extracted_results={"energy": -76.0},
        )
        monkeypatch.setattr(
            "frank.core.executor.PySCFExecutor.execute_with_recovery",
            lambda self, script, job_name, original_basis=None: (fake_result, []),
        )

        repo = JobRepository()
        job_id = repo.create_job(molecule_name="water", method="HF", status="pending")
        celery_id = submit_single_job(job_id, "print(1)", "water_hf")
        assert celery_id

        job = repo.get_job(job_id)
        assert job["status"] == "completed"
