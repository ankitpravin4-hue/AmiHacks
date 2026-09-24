"""FastAPI application: REST + WebSocket around ScanEngine."""

from __future__ import annotations

import asyncio
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import UploadFile

from sentinel_core.ai import LLMRemediationAdvisor, is_configured
from sentinel_core.ai.gemini import AI_NOT_CONFIGURED, AI_RATE_LIMITED, AI_UNAVAILABLE
from sentinel_core.engine import ScanEngine
from sentinel_core.http_client import default_allowlist, url_is_allowed
from sentinel_core.models import Finding, Report, ScanConfig
from sentinel_core.spec_parser import SpecParseError, SpecParser
from sentinel_core.spec_static import SPEC_ONLY_TARGET
from sentinel_core.storage import DEFAULT_DB_PATH, Storage, configure, get_storage
from sentinel_service.presets import resolve_identities_file
from sentinel_service.progress import ProgressHub
from sentinel_service.replay import replay_finding
from sentinel_service.schemas import (
    AIAnswer,
    AskQuestion,
    ReplayResult,
    SPEC_TEXT_MAX,
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
    async def start_scan(request: Request) -> ScanAccepted:
        """Queue a background scan. Live URL is allow-listed; spec-only is static."""
        body = await _read_scan_create(request)
        target, spec_url, spec_text = _prepare_scan_inputs(body, app.state.allowlist)
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
            target=target or SPEC_ONLY_TARGET,
            spec_url=spec_url,
            spec_text=spec_text,
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
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/scans/{scan_id}/findings/{finding_key}/explain", response_model=AIAnswer)
    async def explain_finding(scan_id: int, finding_key: str) -> AIAnswer:
        """On-demand Gemini explanation of one stored finding. Never runs during a scan."""
        finding = get_storage().get_finding(scan_id, finding_key)
        if finding is None:
            raise HTTPException(status_code=404, detail=f"Finding {finding_key!r} not in scan {scan_id}")
        text = await asyncio.to_thread(LLMRemediationAdvisor().advise, finding)
        return _ai_answer(text)

    @app.post("/scans/{scan_id}/ask", response_model=AIAnswer)
    async def ask_scan(scan_id: int, body: AskQuestion) -> AIAnswer:
        """On-demand Gemini Q&A about this scan's findings and chains."""
        question = body.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question is required")
        report = _require_report(get_storage(), scan_id)
        text = await asyncio.to_thread(
            LLMRemediationAdvisor().answer,
            question,
            report.findings,
            report.chains,
            report.target,
        )
        return _ai_answer(text)

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


async def _read_scan_create(request: Request) -> ScanCreate:
    """Accept JSON or multipart (spec file upload) on POST /scans."""
    content_type = (request.headers.get("content-type") or "").lower()
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        spec_text = _form_str(form.get("spec_text"))
        upload = form.get("spec_file") or form.get("spec")
        if isinstance(upload, UploadFile):
            raw = await upload.read()
            try:
                spec_text = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise HTTPException(
                    status_code=400,
                    detail="Spec file must be UTF-8 OpenAPI/Swagger JSON or YAML.",
                ) from exc
        return ScanCreate(
            target_base_url=_form_str(form.get("target_base_url")),
            spec_url=_form_str(form.get("spec_url")),
            spec_text=spec_text,
            identities_preset=_form_str(form.get("identities_preset")) or "shopapi",
            safe_mode=_form_bool(form.get("safe_mode"), default=True),
        )
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Request body must be JSON or a spec file.") from exc
    return ScanCreate.model_validate(payload)


def _form_str(value: object) -> str | None:
    if value is None or isinstance(value, UploadFile):
        return None
    text = str(value).strip()
    return text or None


def _form_bool(value: object, *, default: bool) -> bool:
    if value is None or isinstance(value, UploadFile):
        return default
    return str(value).strip().lower() not in {"0", "false", "no"}


def _prepare_scan_inputs(
    body: ScanCreate,
    allowlist: list[str],
) -> tuple[str | None, str | None, str | None]:
    spec_text = (body.spec_text or "").strip() or None
    target = (body.target_base_url or "").strip().rstrip("/") or None
    spec_url = (body.spec_url or "").strip() or None
    if spec_text and len(spec_text) > SPEC_TEXT_MAX:
        raise HTTPException(status_code=400, detail="Spec text is too large (max 1.5 MB).")
    if not target and not spec_text:
        raise HTTPException(
            status_code=400,
            detail="Provide a live target URL or an OpenAPI/Swagger spec (file or pasted text).",
        )
    if spec_text:
        try:
            SpecParser().load_from_text(spec_text)
        except SpecParseError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Could not parse OpenAPI/Swagger spec: {exc}",
            ) from exc
    if target:
        _assert_allowed(target, allowlist)
        if spec_text:
            spec_url = None
        else:
            spec_url = spec_url or f"{target}/openapi.json"
            _assert_allowed(spec_url, allowlist)
    else:
        spec_url = None
    return target, spec_url, spec_text


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


def _ai_answer(text: str) -> AIAnswer:
    configured = is_configured()
    generated = configured and text not in {AI_NOT_CONFIGURED, AI_UNAVAILABLE, AI_RATE_LIMITED}
    return AIAnswer(text=text, configured=configured, ai_generated=generated)


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
        skipped_checks=report.skipped_checks,
    )


app = create_app()
