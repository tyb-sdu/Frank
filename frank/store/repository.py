"""Repository layer for CalcStore CRUD operations."""

from __future__ import annotations

import csv
import io
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..molecules.database import get_molecule, get_xyz_block
from .database import get_session, init_db, tables_exist
from .models import JobRecord, MoleculeRecord, ResultRecord, WorkflowJobRecord, WorkflowRecord


@dataclass
class JobSummary:
    id: str
    status: str
    molecule_name: str | None
    method: str | None
    basis: str | None
    calc_type: str | None
    energy_hartree: float | None
    duration_sec: float | None
    created_at: datetime
    error_message: str | None = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _extract_energy(raw: dict | None) -> float | None:
    if not raw:
        return None
    for key in ("energy", "electronic_energy", "e_tot"):
        val = raw.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    return None


def _extract_homo_lumo(raw: dict | None) -> tuple[float | None, float | None]:
    if not raw:
        return None, None
    mo_e = raw.get("mo_energy") or raw.get("mo_energy_alpha")
    mo_o = raw.get("mo_occ") or raw.get("mo_occ_alpha")
    if not mo_e or not mo_o:
        return None, None
    try:
        occupied = [e for e, o in zip(mo_e, mo_o) if o > 0.5]
        virtual = [e for e, o in zip(mo_e, mo_o) if o <= 0.5]
        homo = max(occupied) if occupied else None
        lumo = min(virtual) if virtual else None
        return homo, lumo
    except Exception:
        return None, None


def _extract_dipole(raw: dict | None) -> float | None:
    if not raw:
        return None
    dip = raw.get("dipole")
    if dip is None:
        return None
    try:
        return math.sqrt(sum(float(x) ** 2 for x in dip))
    except Exception:
        return None


class JobRepository:
    """High-level database operations for jobs, molecules, and workflows."""

    def __init__(self, session: Session | None = None):
        self._session = session

    def _session_ctx(self):
        if self._session is not None:
            from contextlib import nullcontext
            return nullcontext(self._session)
        return get_session()

    def ensure_tables(self) -> None:
        if not tables_exist():
            init_db()

    def get_or_create_molecule(
        self,
        name: str,
        *,
        formula: str | None = None,
        smiles: str | None = None,
        xyz_content: str | None = None,
        session: Session | None = None,
    ) -> str:
        def _impl(sess: Session) -> str:
            xyz = xyz_content
            formula_local = formula
            smiles_local = smiles
            if xyz is None:
                try:
                    mol = get_molecule(name)
                    xyz = get_xyz_block(mol)
                    formula_local = formula_local or mol.formula
                    smiles_local = smiles_local or mol.smiles
                except KeyError:
                    xyz = None

            stmt = select(MoleculeRecord).where(MoleculeRecord.name == name)
            if xyz:
                stmt = stmt.where(MoleculeRecord.xyz_content == xyz)
            existing = sess.scalar(stmt)
            if existing:
                return existing.id

            record = MoleculeRecord(
                name=name,
                formula=formula_local,
                smiles=smiles_local,
                xyz_content=xyz,
            )
            sess.add(record)
            sess.flush()
            return record.id

        if session is not None:
            return _impl(session)
        with self._session_ctx() as sess:
            return _impl(sess)

    def create_job(
        self,
        *,
        molecule_name: str | None = None,
        method: str | None = None,
        basis: str | None = None,
        calc_type: str | None = None,
        query_text: str | None = None,
        script_path: str | None = None,
        run_dir: str | None = None,
        job_name: str | None = None,
        status: str = "pending",
        celery_id: str | None = None,
    ) -> str:
        with self._session_ctx() as session:
            mol_id = None
            if molecule_name:
                mol_id = self.get_or_create_molecule(molecule_name, session=session)

            job = JobRecord(
                molecule_id=mol_id,
                method=method,
                basis=basis,
                calc_type=calc_type,
                query_text=query_text,
                script_path=script_path,
                run_dir=run_dir,
                job_name=job_name,
                status=status,
                celery_id=celery_id,
            )
            session.add(job)
            session.flush()
            return job.id

    def update_status(
        self,
        job_id: str,
        status: str,
        *,
        celery_id: str | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        duration_sec: float | None = None,
        run_dir: str | None = None,
        script_path: str | None = None,
    ) -> None:
        with self._session_ctx() as session:
            job = session.get(JobRecord, job_id)
            if not job:
                raise KeyError(f"Job not found: {job_id}")
            job.status = status
            if celery_id is not None:
                job.celery_id = celery_id
            if error_type is not None:
                job.error_type = error_type
            if error_message is not None:
                job.error_message = error_message
            if duration_sec is not None:
                job.duration_sec = duration_sec
            if run_dir is not None:
                job.run_dir = run_dir
            if script_path is not None:
                job.script_path = script_path
            now = _utcnow()
            if status == "running" and job.started_at is None:
                job.started_at = now
            if status in ("completed", "failed", "cancelled"):
                job.finished_at = now

    def save_result(self, job_id: str, extracted_results: dict, execution_success: bool = True) -> None:
        with self._session_ctx() as session:
            job = session.get(JobRecord, job_id)
            if not job:
                raise KeyError(f"Job not found: {job_id}")

            energy = _extract_energy(extracted_results)
            homo, lumo = _extract_homo_lumo(extracted_results)
            dipole = _extract_dipole(extracted_results)
            nimag = extracted_results.get("n_imaginary") or extracted_results.get("nimag")

            if job.result:
                result = job.result
            else:
                result = ResultRecord(job_id=job_id)
                session.add(result)

            result.energy_hartree = energy
            result.enthalpy = extracted_results.get("enthalpy")
            result.free_energy = extracted_results.get("free_energy") or extracted_results.get("gibbs")
            result.homo_ev = homo
            result.lumo_ev = lumo
            result.dipole_debye = dipole
            if nimag is not None:
                try:
                    result.nimag_freq = int(nimag)
                except (TypeError, ValueError):
                    pass
            result.raw_json = extracted_results

            job.status = "completed" if execution_success else "failed"
            job.finished_at = _utcnow()

    def _serialize_job(self, job: JobRecord) -> dict:
        res = job.result
        mol = job.molecule
        return {
            "id": job.id,
            "status": job.status,
            "celery_id": job.celery_id,
            "molecule": mol.name if mol else None,
            "method": job.method,
            "basis": job.basis,
            "calc_type": job.calc_type,
            "duration_sec": job.duration_sec,
            "energy_hartree": res.energy_hartree if res else None,
            "homo_ev": res.homo_ev if res else None,
            "lumo_ev": res.lumo_ev if res else None,
            "dipole_debye": res.dipole_debye if res else None,
            "error_type": job.error_type,
            "error_message": job.error_message,
            "run_dir": job.run_dir,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        }

    def get_job(self, job_id: str) -> dict | None:
        with self._session_ctx() as session:
            stmt = (
                select(JobRecord)
                .options(joinedload(JobRecord.molecule), joinedload(JobRecord.result))
                .where(JobRecord.id == job_id)
            )
            job = session.scalar(stmt)
            return self._serialize_job(job) if job else None

    def get_job_by_celery_id(self, celery_id: str) -> JobRecord | None:
        with self._session_ctx() as session:
            stmt = select(JobRecord).where(JobRecord.celery_id == celery_id)
            return session.scalar(stmt)

    def list_jobs(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        molecule: str | None = None,
        method: str | None = None,
        status: str | None = None,
    ) -> list[JobSummary]:
        with self._session_ctx() as session:
            stmt = (
                select(JobRecord, MoleculeRecord, ResultRecord)
                .outerjoin(MoleculeRecord, JobRecord.molecule_id == MoleculeRecord.id)
                .outerjoin(ResultRecord, JobRecord.id == ResultRecord.job_id)
                .order_by(JobRecord.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            if molecule:
                stmt = stmt.where(MoleculeRecord.name.ilike(f"%{molecule}%"))
            if method:
                stmt = stmt.where(JobRecord.method.ilike(f"%{method}%"))
            if status:
                stmt = stmt.where(JobRecord.status == status)

            rows = session.execute(stmt).all()
            summaries = []
            for job, mol, result in rows:
                summaries.append(
                    JobSummary(
                        id=job.id,
                        status=job.status,
                        molecule_name=mol.name if mol else None,
                        method=job.method,
                        basis=job.basis,
                        calc_type=job.calc_type,
                        energy_hartree=result.energy_hartree if result else None,
                        duration_sec=job.duration_sec,
                        created_at=job.created_at,
                        error_message=job.error_message,
                    )
                )
            return summaries

    def compare_jobs(self, job_id_a: str, job_id_b: str) -> dict:
        a = self.get_job(job_id_a)
        b = self.get_job(job_id_b)
        if not a or not b:
            raise KeyError("One or both jobs not found")

        delta = {}
        if a["energy_hartree"] is not None and b["energy_hartree"] is not None:
            delta["energy_hartree"] = b["energy_hartree"] - a["energy_hartree"]
            delta["energy_kcal_mol"] = delta["energy_hartree"] * 627.51
        return {"job_a": a, "job_b": b, "delta": delta}

    def export_csv(
        self,
        *,
        molecule: str | None = None,
        method: str | None = None,
        limit: int = 1000,
    ) -> str:
        jobs = self.list_jobs(limit=limit, molecule=molecule, method=method)
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=[
                "id", "status", "molecule", "method", "basis", "calc_type",
                "energy_hartree", "duration_sec", "created_at", "error_message",
            ],
        )
        writer.writeheader()
        for j in jobs:
            writer.writerow({
                "id": j.id,
                "status": j.status,
                "molecule": j.molecule_name or "",
                "method": j.method or "",
                "basis": j.basis or "",
                "calc_type": j.calc_type or "",
                "energy_hartree": j.energy_hartree if j.energy_hartree is not None else "",
                "duration_sec": j.duration_sec if j.duration_sec is not None else "",
                "created_at": j.created_at.isoformat() if j.created_at else "",
                "error_message": j.error_message or "",
            })
        return buf.getvalue()

    def export_json(self, **filters) -> str:
        jobs = self.list_jobs(limit=filters.get("limit", 1000), **{k: v for k, v in filters.items() if k != "limit"})
        return json.dumps([j.__dict__ for j in jobs], default=str, indent=2, ensure_ascii=False)

    def create_workflow(
        self,
        *,
        title: str,
        workflow_type: str,
        plan_json: dict,
        query_text: str | None = None,
        status: str = "pending",
    ) -> str:
        with self._session_ctx() as session:
            wf = WorkflowRecord(
                title=title,
                workflow_type=workflow_type,
                plan_json=plan_json,
                query_text=query_text,
                status=status,
            )
            session.add(wf)
            session.flush()
            return wf.id

    def link_workflow_job(self, workflow_id: str, job_id: str, step_order: int) -> None:
        with self._session_ctx() as session:
            link = WorkflowJobRecord(
                workflow_id=workflow_id,
                job_id=job_id,
                step_order=step_order,
            )
            session.add(link)

    def update_workflow_status(self, workflow_id: str, status: str) -> None:
        with self._session_ctx() as session:
            wf = session.get(WorkflowRecord, workflow_id)
            if not wf:
                raise KeyError(f"Workflow not found: {workflow_id}")
            wf.status = status
            if status in ("completed", "failed", "cancelled"):
                wf.finished_at = _utcnow()

    def get_workflow(self, workflow_id: str) -> dict | None:
        with self._session_ctx() as session:
            stmt = (
                select(WorkflowRecord)
                .options(
                    joinedload(WorkflowRecord.job_links).joinedload(WorkflowJobRecord.job).joinedload(JobRecord.result),
                    joinedload(WorkflowRecord.job_links).joinedload(WorkflowJobRecord.job).joinedload(JobRecord.molecule),
                )
                .where(WorkflowRecord.id == workflow_id)
            )
            wf = session.scalar(stmt)
            if not wf:
                return None
            steps = []
            for link in sorted(wf.job_links, key=lambda l: l.step_order):
                job = link.job
                res = job.result
                mol = job.molecule
                steps.append({
                    "step": link.step_order,
                    "job_id": job.id,
                    "molecule": mol.name if mol else None,
                    "status": job.status,
                    "energy_hartree": res.energy_hartree if res else None,
                })
            return {
                "id": wf.id,
                "title": wf.title,
                "workflow_type": wf.workflow_type,
                "status": wf.status,
                "steps": steps,
                "created_at": wf.created_at.isoformat() if wf.created_at else None,
            }
