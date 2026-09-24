"""Typer entry point: `sentinel scan`."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer

from sentinel_cli.formatters import render_json, render_junit, render_sarif, render_table, validate_sarif
from sentinel_cli.gate import EXIT_CLEAN, EXIT_ERROR, EXIT_GATE_FAILED, findings_at_or_above, gate_message
from sentinel_core.engine import ScanEngine
from sentinel_core.http_client import default_allowlist, url_is_allowed
from sentinel_core.models import ScanConfig

SCANNER_ROOT = Path(__file__).resolve().parent.parent
PRESETS = {
    "shopapi": SCANNER_ROOT / "configs" / "shopapi.identities.yaml",
}

app = typer.Typer(
    name="sentinel",
    help="SentinelAPI CI/CD gate — scan an allow-listed API and fail the build on severity.",
    no_args_is_help=True,
)


@app.callback()
def _root() -> None:
    """SentinelAPI CI/CD gate."""
    return None


def _progress(percent: int, step: str) -> None:
    print(f"\r[{percent:3d}%] {step:<56}", file=sys.stderr, end="", flush=True)
    if percent >= 100:
        print(file=sys.stderr)


def _resolve_identities(value: str) -> Path:
    """Accept a preset name (`shopapi`) or a path to an identities YAML."""
    preset = PRESETS.get(value.lower())
    if preset is not None:
        if not preset.is_file():
            raise FileNotFoundError(f"Preset file missing: {preset}")
        return preset
    path = Path(value).expanduser()
    if not path.is_file():
        raise FileNotFoundError(
            f"Identities file not found: {value} (known presets: {', '.join(sorted(PRESETS))})"
        )
    return path


def _render(report, fmt: str) -> str:
    if fmt == "table":
        return render_table(report)
    if fmt == "json":
        return render_json(report)
    if fmt == "sarif":
        text = render_sarif(report)
        import json

        validate_sarif(json.loads(text))
        return text
    if fmt == "junit":
        return render_junit(report)
    raise ValueError(f"Unknown format {fmt!r}")


@app.command("scan")
def scan_cmd(
    target: str = typer.Option(..., "--target", help="Allow-listed API base URL"),
    identities: str = typer.Option(
        "shopapi",
        "--identities",
        help="Preset name (shopapi) or path to an identities YAML",
    ),
    spec: Optional[str] = typer.Option(
        None,
        "--spec",
        help="OpenAPI URL (default: <target>/openapi.json)",
    ),
    fail_on: str = typer.Option(
        "high",
        "--fail-on",
        help="Minimum severity that fails the gate: critical|high|medium|low",
    ),
    fmt: str = typer.Option(
        "table",
        "--format",
        help="table | json | sarif | junit",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write the report to this path instead of stdout",
    ),
) -> None:
    """Run a full ScanEngine pass and exit 1 if findings meet --fail-on."""
    fail_on_n = fail_on.lower()
    if fail_on_n not in {"critical", "high", "medium", "low"}:
        typer.echo(f"Invalid --fail-on {fail_on!r}", err=True)
        raise typer.Exit(EXIT_ERROR)
    fmt_n = fmt.lower()
    if fmt_n not in {"table", "json", "sarif", "junit"}:
        typer.echo(f"Invalid --format {fmt!r}", err=True)
        raise typer.Exit(EXIT_ERROR)

    allowlist = default_allowlist()
    spec_url = spec or f"{target.rstrip('/')}/openapi.json"
    if not url_is_allowed(target, allowlist):
        typer.echo(
            f"Refusing to scan {target} — not on the allow-list ({', '.join(allowlist)}).",
            err=True,
        )
        raise typer.Exit(EXIT_ERROR)
    if not url_is_allowed(spec_url, allowlist):
        typer.echo(
            f"Refusing to fetch spec {spec_url} — not on the allow-list ({', '.join(allowlist)}).",
            err=True,
        )
        raise typer.Exit(EXIT_ERROR)

    try:
        identities_file = _resolve_identities(identities)
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(EXIT_ERROR) from exc

    config = ScanConfig(
        target=target.rstrip("/"),
        spec_url=spec_url,
        allowlist=allowlist,
        identities_file=str(identities_file),
        safe_mode=True,
    )
    try:
        report = asyncio.run(ScanEngine().run(config, on_progress=_progress))
    except Exception as exc:
        typer.echo(f"Scan failed: {exc}", err=True)
        raise typer.Exit(EXIT_ERROR) from exc

    try:
        text = _render(report, fmt_n)
    except Exception as exc:
        typer.echo(f"Failed to render {fmt_n}: {exc}", err=True)
        raise typer.Exit(EXIT_ERROR) from exc

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")
        typer.echo(f"Wrote {fmt_n} report to {output}", err=True)
        if fmt_n == "table":
            typer.echo(text)
    else:
        typer.echo(text)

    breaches = findings_at_or_above(report.findings, fail_on_n)
    typer.echo(gate_message(breaches, fail_on_n), err=True)
    raise typer.Exit(EXIT_GATE_FAILED if breaches else EXIT_CLEAN)
