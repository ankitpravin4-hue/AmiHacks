"""SQLite persistence for scan reports via SQLModel."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, desc
from sqlmodel import Field, Session, SQLModel, create_engine, select

from sentinel_core.models import Finding, Report

SCANNER_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = SCANNER_ROOT / "data" / "sentinel.db"

_engine: Engine | None = None


class ScanReportRow(SQLModel, table=True):
    """One persisted scan. ``payload`` is the full Report JSON."""

    __tablename__ = "scan_reports"

    id: int | None = Field(default=None, primary_key=True)
    target: str
    payload: str


class FindingRow(SQLModel, table=True):
    """Finding row so Phase 5 can fetch one item without the whole report."""

    __tablename__ = "findings"

    id: int | None = Field(default=None, primary_key=True)
    report_id: int = Field(index=True, foreign_key="scan_reports.id")
    finding_key: str = Field(index=True)
    payload: str


def configure(db_path: Path | str | None = None) -> Engine:
    """Create (or replace) the module-level engine and ensure tables exist."""
    global _engine
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    _engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(_engine)
    return _engine


def get_engine() -> Engine:
    """Return the configured engine, initializing the default DB if needed."""
    if _engine is None:
        return configure()
    return _engine


def save_report(report: Report) -> Report:
    """Insert a report and its findings. Sets ``report.id`` to the new PK."""
    dumped = report.model_copy(update={"id": None})
    with Session(get_engine()) as session:
        row = ScanReportRow(target=report.target, payload=dumped.model_dump_json())
        session.add(row)
        session.commit()
        session.refresh(row)
        assert row.id is not None
        report.id = row.id
        row.payload = report.model_dump_json()
        for finding in report.findings:
            session.add(
                FindingRow(
                    report_id=row.id,
                    finding_key=finding.id,
                    payload=finding.model_dump_json(),
                )
            )
        session.add(row)
        session.commit()
    return report


def list_reports() -> list[Report]:
    """All stored reports, newest first."""
    with Session(get_engine()) as session:
        rows = session.exec(select(ScanReportRow).order_by(desc(ScanReportRow.id))).all()
        return [_row_to_report(row) for row in rows]


def get_report(report_id: int) -> Report | None:
    """Load one report by SQLite id, or None if missing."""
    with Session(get_engine()) as session:
        row = session.get(ScanReportRow, report_id)
        if row is None:
            return None
        return _row_to_report(row)


def get_finding(report_id: int, finding_id: str) -> Finding | None:
    """Load one finding belonging to ``report_id``."""
    with Session(get_engine()) as session:
        statement = select(FindingRow).where(
            FindingRow.report_id == report_id,
            FindingRow.finding_key == finding_id,
        )
        row = session.exec(statement).first()
        if row is None:
            return None
        return Finding.model_validate_json(row.payload)


def _row_to_report(row: ScanReportRow) -> Report:
    report = Report.model_validate_json(row.payload)
    report.id = row.id
    return report
