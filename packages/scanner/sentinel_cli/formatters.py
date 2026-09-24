"""Report renderers: table, JSON, SARIF 2.1.0, and JUnit XML."""

from __future__ import annotations

import json
from collections import defaultdict
from xml.etree.ElementTree import Element, SubElement, tostring

from sentinel_core.models import Finding, Report

from sentinel_cli.gate import SEVERITY_RANK

_SARIF_LEVEL = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
}


def render_table(report: Report) -> str:
    """Severity-sorted summary plus counts and chain names."""
    findings = sorted(
        report.findings,
        key=lambda item: (
            -SEVERITY_RANK.get(item.severity_label.lower(), 0),
            -item.severity_score,
        ),
    )
    headers = ("SEV", "SCORE", "CLASS", "ENDPOINT", "IMPACT")
    rows = [
        (
            item.severity_label,
            f"{item.severity_score:.1f}",
            item.vuln_class,
            item.endpoint,
            _one_line(item.business_impact),
        )
        for item in findings
    ]
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    lines = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * widths[index] for index in range(len(headers))),
    ]
    for row in rows:
        lines.append(
            "  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row))
        )
    counts = report.summary.by_severity
    count_bits = [f"{counts.get(label, 0)} {label}" for label in ("Critical", "High", "Medium", "Low") if counts.get(label)]
    lines.append("")
    lines.append(
        f"{report.summary.total_findings} findings  |  "
        + (", ".join(count_bits) if count_bits else "none")
    )
    if report.chains:
        names = ", ".join(chain.id for chain in report.chains)
        lines.append(f"Chains: {names}")
    else:
        lines.append("Chains: (none)")
    return "\n".join(lines)


def render_json(report: Report) -> str:
    """Full report JSON (datetimes as ISO strings)."""
    return json.dumps(report.model_dump(mode="json"), indent=2)


def render_sarif(report: Report) -> str:
    """SARIF 2.1.0 document GitHub code scanning can ingest."""
    rules_by_id: dict[str, dict] = {}
    results: list[dict] = []
    for finding in report.findings:
        if finding.vuln_class not in rules_by_id:
            rules_by_id[finding.vuln_class] = {
                "id": finding.vuln_class,
                "name": finding.vuln_class,
                "shortDescription": {"text": finding.title or finding.vuln_class},
                "fullDescription": {"text": finding.business_impact or finding.title},
                "help": {"text": finding.remediation or finding.business_impact},
                "helpUri": "https://owasp.org/API-Security/",
                "defaultConfiguration": {
                    "level": _SARIF_LEVEL.get(finding.severity_label.lower(), "warning")
                },
            }
        uri = _sarif_uri(finding.endpoint)
        results.append(
            {
                "ruleId": finding.vuln_class,
                "level": _SARIF_LEVEL.get(finding.severity_label.lower(), "warning"),
                "message": {"text": finding.business_impact or finding.title},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": uri},
                            "region": {"startLine": 1},
                        },
                        "logicalLocations": [
                            {
                                "fullyQualifiedName": finding.endpoint,
                                "kind": "function",
                            }
                        ],
                    }
                ],
                "properties": {
                    "endpoint": finding.endpoint,
                    "poc_curl": finding.poc_curl,
                    "severity_score": finding.severity_score,
                    "severity_label": finding.severity_label,
                    "finding_id": finding.id,
                },
            }
        )
    document = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "SentinelAPI",
                        "version": "0.6.0",
                        "informationUri": "https://github.com/sentinelapi/sentinelapi",
                        "rules": list(rules_by_id.values()),
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(document, indent=2)


def render_junit(report: Report) -> str:
    """JUnit XML: one testcase per endpoint; each finding is a failure."""
    grouped: dict[str, list[Finding]] = defaultdict(list)
    for finding in report.findings:
        grouped[finding.endpoint].append(finding)
    suite = Element(
        "testsuite",
        {
            "name": "sentinel",
            "tests": str(len(grouped)),
            "failures": str(len(report.findings)),
        },
    )
    for endpoint, items in grouped.items():
        case = SubElement(
            suite,
            "testcase",
            {"classname": "sentinel.scan", "name": endpoint, "time": "0"},
        )
        details = []
        for item in items:
            details.append(
                f"[{item.severity_label} {item.severity_score}] {item.vuln_class}\n"
                f"{item.business_impact}\n{item.poc_curl}"
            )
        failure = SubElement(
            case,
            "failure",
            {
                "message": f"{len(items)} finding(s) on {endpoint}",
                "type": items[0].vuln_class,
            },
        )
        failure.text = "\n\n".join(details)
    xml = tostring(suite, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml}\n'


def validate_sarif(document: dict) -> None:
    """Raise ``ValueError`` if the payload is not a usable SARIF 2.1.0 run."""
    if document.get("version") != "2.1.0":
        raise ValueError("SARIF version must be 2.1.0")
    runs = document.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("SARIF must contain a non-empty runs array")
    driver = ((runs[0] or {}).get("tool") or {}).get("driver") or {}
    if not driver.get("name"):
        raise ValueError("SARIF driver.name is required")
    rules = {rule.get("id") for rule in driver.get("rules") or [] if isinstance(rule, dict)}
    for result in runs[0].get("results") or []:
        if not result.get("ruleId"):
            raise ValueError("Each SARIF result needs ruleId")
        if result["ruleId"] not in rules:
            raise ValueError(f"ruleId {result['ruleId']!r} is not declared in driver.rules")
        message = result.get("message") or {}
        if not message.get("text"):
            raise ValueError("Each SARIF result needs message.text")
        if result.get("level") not in {"error", "warning", "note", "none"}:
            raise ValueError(f"Invalid SARIF level {result.get('level')!r}")


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _sarif_uri(endpoint: str) -> str:
    """Stable, file-like URI so GitHub can attach the result to a location."""
    cleaned = endpoint.strip().replace(" ", "/")
    return f"api/{cleaned.lstrip('/')}"
