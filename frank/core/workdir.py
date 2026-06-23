"""Persistent run directories — Aitomia-style reproducible job folders."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import get_runs_dir, get_save_runs


class RunDirectory:
    """Manage a single Frank calculation run directory."""

    def __init__(self, path: Path, job_name: str):
        self.path = path
        self.job_name = job_name
        self.path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def create(cls, job_name: str = "frank_job", base_dir: Optional[str] = None) -> RunDirectory:
        base = Path(base_dir or get_runs_dir())
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in job_name)[:40]
        run_path = base / f"{stamp}_{safe_name}"
        return cls(run_path, job_name)

    def write_script(self, script: str, name: Optional[str] = None) -> Path:
        script_path = self.path / (name or f"{self.job_name}.py")
        script_path.write_text(script, encoding="utf-8")
        return script_path

    def write_metadata(self, metadata: dict) -> Path:
        meta_path = self.path / "metadata.json"
        existing = {}
        if meta_path.exists():
            try:
                existing = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        existing.update(metadata)
        existing["updated_at"] = datetime.now().isoformat()
        meta_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        return meta_path

    def save_execution(self, execution_result, extra: Optional[dict] = None) -> None:
        """Persist stdout/stderr and summary after a calculation."""
        if execution_result.stdout:
            (self.path / "stdout.log").write_text(execution_result.stdout, encoding="utf-8")
        if execution_result.stderr:
            (self.path / "stderr.log").write_text(execution_result.stderr, encoding="utf-8")
        if execution_result.log_content:
            (self.path / "pyscf.log").write_text(execution_result.log_content, encoding="utf-8")

        summary = {
            "success": execution_result.success,
            "return_code": execution_result.return_code,
            "duration": execution_result.duration,
            "error_type": execution_result.error_type,
            "error_message": execution_result.error_message,
            "extracted_results": execution_result.extracted_results,
        }
        if extra:
            summary.update(extra)
        (self.path / "results.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def copy_file(self, src: Path, dest_name: Optional[str] = None) -> Path:
        dest = self.path / (dest_name or src.name)
        shutil.copy2(src, dest)
        return dest

    def __str__(self) -> str:
        return str(self.path)


def should_persist_runs() -> bool:
    return get_save_runs()


def create_run_directory(job_name: str = "frank_job", work_dir: Optional[str] = None) -> Optional[RunDirectory]:
    """Create a persistent run directory, or return None if persistence is disabled."""
    if work_dir:
        path = Path(work_dir)
        path.mkdir(parents=True, exist_ok=True)
        return RunDirectory(path, job_name)
    if not should_persist_runs():
        return None
    return RunDirectory.create(job_name)
