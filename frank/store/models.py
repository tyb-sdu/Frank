"""SQLAlchemy ORM models for CalcStore."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class MoleculeRecord(Base):
    __tablename__ = "molecules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    formula: Mapped[str | None] = mapped_column(String(64))
    smiles: Mapped[str | None] = mapped_column(Text)
    inchi: Mapped[str | None] = mapped_column(Text)
    xyz_content: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    jobs: Mapped[list[JobRecord]] = relationship(back_populates="molecule")

    __table_args__ = (UniqueConstraint("name", "xyz_content", name="uq_molecule_name_xyz"),)


class JobRecord(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    celery_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    molecule_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("molecules.id"))
    query_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    method: Mapped[str | None] = mapped_column(String(64))
    basis: Mapped[str | None] = mapped_column(String(64))
    calc_type: Mapped[str | None] = mapped_column(String(64))
    script_path: Mapped[str | None] = mapped_column(Text)
    run_dir: Mapped[str | None] = mapped_column(Text)
    job_name: Mapped[str | None] = mapped_column(String(128))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    error_type: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_sec: Mapped[float | None] = mapped_column(Float)

    molecule: Mapped[MoleculeRecord | None] = relationship(back_populates="jobs")
    result: Mapped[ResultRecord | None] = relationship(back_populates="job", uselist=False)
    workflow_links: Mapped[list[WorkflowJobRecord]] = relationship(back_populates="job")


class ResultRecord(Base):
    __tablename__ = "results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), unique=True)
    energy_hartree: Mapped[float | None] = mapped_column(Float)
    enthalpy: Mapped[float | None] = mapped_column(Float)
    free_energy: Mapped[float | None] = mapped_column(Float)
    homo_ev: Mapped[float | None] = mapped_column(Float)
    lumo_ev: Mapped[float | None] = mapped_column(Float)
    dipole_debye: Mapped[float | None] = mapped_column(Float)
    nimag_freq: Mapped[int | None] = mapped_column(Integer)
    raw_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    job: Mapped[JobRecord] = relationship(back_populates="result")


class WorkflowRecord(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    celery_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    title: Mapped[str | None] = mapped_column(String(256))
    workflow_type: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    plan_json: Mapped[dict | None] = mapped_column(JSON)
    query_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job_links: Mapped[list[WorkflowJobRecord]] = relationship(back_populates="workflow")


class WorkflowJobRecord(Base):
    __tablename__ = "workflow_jobs"

    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    step_order: Mapped[int] = mapped_column(Integer, default=0)

    workflow: Mapped[WorkflowRecord] = relationship(back_populates="job_links")
    job: Mapped[JobRecord] = relationship(back_populates="workflow_links")
