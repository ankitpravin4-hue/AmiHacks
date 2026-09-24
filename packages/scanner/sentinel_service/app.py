"""FastAPI application: REST + WebSocket around ScanEngine."""

from __future__ import annotations

import asyncio
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from sentinel_core.engine import ScanEngine
from sentinel_core.http_client import default_allowlist, url_is_allowed
from sentinel_core.models import Finding, Report, ScanConfig
from sentinel_core.storage import DEFAULT_DB_PATH, Storage, configure, get_storage
from sentinel_service.presets import resolve_identities_file
from sentinel_service.progress import ProgressHub
from sentinel_service.replay import replay_finding
from sentinel_service.schemas import (
    ReplayResult,
    ScanAccepted,
    ScanCreate,
    ScanDetail,
    ScanDiff,
    ScanListItem,
)

DASHBOARD_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def create_app(
    *,
    db_path: Path | str | None = None,
    allowlist: list[str] | None = None,
) -> FastAPI:
    """Build the service app. Tests pass an isolated SQLite path."""
    configure(db_path)
    app = FastAPI(
        title="SentinelAPI Scanner Service",
        description="Allow-listed scan API wrapping sentinel_core.ScanEngine.",
        version="0.5.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(DASHBOARD_ORIGINS),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.db_path = db_path
    app.state.allowlist = [item.rstrip("/") for item in (allowlist or default_allowlist())]
    app.state.hub = ProgressHub()
    app.state.tasks = set()

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        """Liveness probe for run scripts."""
        return {"status": "ok", "service": "sentinel-service"}

    @app.post("/scans", response_model=ScanAccepted)
    async def start_scan(body: ScanCreate) -> ScanAccepted:
        """Queue a background scan. Rejects non-allow-listed targets with 400."""
        _assert_allowed(body.target_base_url, app.state.allowlist)
        spec_url = body.spec_url or f"{body.target_base_url.rstrip('/')}/openapi.json"
        _assert_allowed(spec_url, app.state.allowlist)
        try:
            dest = Path(app.state.db_path).parent if app.state.db_path else DEFAULT_DB_PATH.parent
            identities_file = resolve_identities_file(
                body.identities_preset,
                body.identities_config,
                dest,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        config = ScanConfig(
            target=body.target_base_url.rstrip("/"),
            spec_url=spec_url,
            allowlist=list(app.state.allowlist),
            safe_mode=body.safe_mode,
            identities_file=str(identities_file),
        )
        storage = get_storage()
        placeholder = storage.create_running(config.target, config)
        assert placeholder.id is not None
        task = asyncio.create_task(
            _run_scan(app, placeholder.id, config),
            name=f"scan-{placeholder.id}",
        )
        app.state.tasks.add(task)
        task.add_done_callback(app.state.tasks.discard)
        return ScanAccepted(scan_id=placeholder.id, status="running")

    @app.get("/scans", response_model=list[ScanListItem])
    def list_scans() -> list[ScanListItem]:
        """Past scans for the history / diff view."""
        return [_list_item(report) for report in get_storage().list_reports() if report.id is not None]

    @app.get("/scans/diff", response_model=ScanDiff)
    def diff_scans(a: int, b: int) -> ScanDiff:
        """Compare two scans by finding key: new / fixed / persisting."""
        storage = get_storage()
        left = _require_report(storage, a)
        right = _require_report(storage, b)
        keys_a = {item.id for item in left.findings}
        keys_b = {item.id for item in right.findings}
        return ScanDiff(
            a=a,
            b=b,
            new=sorted(keys_b - keys_a),
            fixed=sorted(keys_a - keys_b),
            persisting=sorted(keys_a & keys_b),
        )

    @app.get("/scans/{scan_id}", response_model=ScanDetail)
    def get_scan(scan_id: int) -> ScanDetail:
        """Full report (findings, chains, matrix) plus status."""
        return _detail(_require_report(get_storage(), scan_id))

    @app.get("/scans/{scan_id}/findings/{finding_key}", response_model=Finding)
    def get_one_finding(scan_id: int, finding_key: str) -> Finding:
        """One finding with evidence and severity breakdown."""
        finding = get_storage().get_finding(scan_id, finding_key)
        if finding is None:
            raise HTTPException(status_code=404, detail=f"Finding {finding_key!r} not in scan {scan_id}")
        return finding

    @app.post("/scans/{scan_id}/findings/{finding_key}/replay", response_model=ReplayResult)
    async def replay(scan_id: int, finding_key: str) -> ReplayResult:
        """Re-run the finding's PoC live through SafeClient."""
        storage = get_storage()
        report = _require_report(storage, scan_id)
        finding = storage.get_finding(scan_id, finding_key)
        if finding is None:
            raise HTTPException(status_code=404, detail=f"Finding {finding_key!r} not in scan {scan_id}")
        allow = list(report.scan_config.allowlist or app.state.allowlist)
        try:
            return await replay_finding(
                finding,
                allowed_base_urls=allow,
                safe_mode=report.scan_config.safe_mode,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.websocket("/scans/{scan_id}/progress")
    async def scan_progress(websocket: WebSocket, scan_id: int) -> None:
        """Stream percent + step; close the socket when the scan finishes."""
        await websocket.accept()
        hub: ProgressHub = app.state.hub
        queue = hub.subscribe(scan_id)
        sent: set[tuple[int, str]] = set()
        try:
            for event in hub.history(scan_id):
                key = (int(event["percent"]), str(event["step"]))
                sent.add(key)
                await websocket.send_json(event)
            if hub.is_done(scan_id):
                return
            while True:
                event = await queue.get()
                if event is None:
                    break
                key = (int(event["percent"]), str(event["step"]))
                if key in sent:
                    continue
                sent.add(key)
                await websocket.send_json(event)
        except WebSocketDisconnect:
            return
        finally:
            hub.unsubscribe(scan_id, queue)
            try:
                await websocket.close()
            except Exception:
                pass

    return app


async def _run_scan(app: FastAPI, scan_id: int, config: ScanConfig) -> None:
    """Background worker: never let a scan exception kill the server."""
    hub: ProgressHub = app.state.hub

    def on_progress(percent: int, step: str) -> None:
        hub.emit(scan_id, percent, step)

    try:
        engine = ScanEngine(app.state.db_path)
        await engine.run(config, on_progress=on_progress, scan_id=scan_id)
        hub.emit(scan_id, 100, "Scan completed", status="completed")
    except Exception as exc:
        get_storage().mark_failed(scan_id, str(exc))
        hub.emit(scan_id, 100, f"Scan failed: {exc}", status="failed")


def _assert_allowed(url: str, allowlist: list[str]) -> None:
    if not url_is_allowed(url, allowlist):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Refusing to scan {url} — not on the allow-list "
                f"({', '.join(allowlist)}). SentinelAPI never scans non-allow-listed targets."
            ),
        )


def _require_report(storage: Storage, scan_id: int) -> Report:
    report = storage.get_report(scan_id)
    if report is None or report.id is None:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    return report


def _list_item(report: Report) -> ScanListItem:
    assert report.id is not None
    return ScanListItem(
        id=report.id,
        target=report.target,
        started_at=report.started_at,
        finished_at=report.finished_at,
        status=report.status,
        summary=report.summary,
        error=report.error,
    )


def _detail(report: Report) -> ScanDetail:
    assert report.id is not None
    return ScanDetail(
        id=report.id,
        target=report.target,
        started_at=report.started_at,
        finished_at=report.finished_at,
        status=report.status,
        error=report.error,
        findings=report.findings,
        chains=report.chains,
        access_matrix=report.access_matrix,
        summary=report.summary,
    )


app = create_app()
