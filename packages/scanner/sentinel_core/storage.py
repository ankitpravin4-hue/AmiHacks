"""SQLite persistence for scan reports via SQLModel."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Engine, desc
from sqlmodel import Field, Session, SQLModel, create_engine, select

from sentinel_core.models import Finding, Report, ScanConfig

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
    """Insert or update a report and replace its finding rows."""
    with Session(get_engine()) as session:
        if report.id is not None:
            row = session.get(ScanReportRow, report.id)
            if row is None:
                raise KeyError(f"Unknown report id {report.id}")
            row.target = report.target
            row.payload = report.model_dump_json()
            for existing in session.exec(
                select(FindingRow).where(FindingRow.report_id == report.id)
            ).all():
                session.delete(existing)
            _add_finding_rows(session, report.id, report.findings)
            session.add(row)
            session.commit()
            return report

        dumped = report.model_copy(update={"id": None})
        row = ScanReportRow(target=report.target, payload=dumped.model_dump_json())
        session.add(row)
        session.commit()
        session.refresh(row)
        assert row.id is not None
        report.id = row.id
        row.payload = report.model_dump_json()
        _add_finding_rows(session, row.id, report.findings)
        session.add(row)
        session.commit()
    return report


def _add_finding_rows(session: Session, report_id: int, findings: list[Finding]) -> None:
    for finding in findings:
        session.add(
            FindingRow(
                report_id=report_id,
                finding_key=finding.id,
                payload=finding.model_dump_json(),
            )
        )


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


class Storage:
    """SQLite-backed report store used by the Phase 5 service."""

    def save_report(self, report: Report) -> Report:
        """Persist a report (insert or update)."""
        return save_report(report)

    def list_reports(self) -> list[Report]:
        """Newest-first report list."""
        return list_reports()

    def get_report(self, report_id: int) -> Report | None:
        """Load one report, or None."""
        return get_report(report_id)

    def get_finding(self, report_id: int, finding_id: str) -> Finding | None:
        """Load one finding, or None."""
        return get_finding(report_id, finding_id)

    def create_running(self, target: str, config: ScanConfig) -> Report:
        """Insert a placeholder row so POST /scans can return a scan_id immediately."""
        report = Report(
            target=target,
            started_at=datetime.now(timezone.utc),
            status="running",
            scan_config=config,
        )
        return save_report(report)

    def mark_failed(self, report_id: int, message: str) -> Report | None:
        """Mark a running scan as failed without crashing the API process."""
        report = get_report(report_id)
        if report is None:
            return None
        report.status = "failed"
        report.error = message
        report.finished_at = datetime.now(timezone.utc)
        return save_report(report)


def get_storage() -> Storage:
    """Return the configured SQLite storage facade."""
    get_engine()
    return Storage()
