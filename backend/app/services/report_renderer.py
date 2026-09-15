"""Portable report representations; PDF details remain outside ReportService."""

from __future__ import annotations

import json
from pathlib import Path


def render_markdown(report: dict) -> str:
    if report.get("scope") == "workspace":
        lines = [f"# {report['title']}", "", f"**Period:** {report['period_from']} to {report['period_to']}"]
        if report.get("responsible_person"):
            lines.append(f"**Responsible:** {report['responsible_person']}")
        lines.extend(["", "## Executive summary"] + [f"- {value}" for value in report["executive_summary"]])
        lines.extend(["", "## Projects"])
        for project in report["projects"]:
            lines.extend(["", f"### {project['project']} ({project['status']})"])
            for heading, key in (("Completed work", "completed_work"), ("Results", "major_results"), ("Technical changes", "technical_changes"), ("Validation", "tests_and_validation"), ("Pending", "pending_work"), ("Next steps", "next_steps")):
                lines.append(f"#### {heading}")
                lines.extend([f"- {value}" for value in project[key]] or ["- None recorded"])
        for heading, key in (("Workspace results", "workspace_results"), ("Current blockers", "workspace_blockers"), ("Next priorities", "workspace_next_priorities")):
            lines.extend(["", f"## {heading}"])
            lines.extend([f"- {value}" for value in report[key]] or ["- None recorded"])
        evidence = report["evidence_summary"]
        lines.extend(["", "## Evidence coverage", f"- Coverage: {evidence['coverage']}", f"- Work items considered: {evidence['item_count']}"])
        return "\n".join(lines) + "\n"
    headings = (
        ("Executive summary", "executive_summary"), ("Completed work", "completed_work"),
        ("Major results", "major_results"), ("Technical changes", "technical_changes"),
        ("Tests and validation", "tests_and_validation"), ("Deployments", "deployments"),
        ("Problems resolved", "problems_resolved"), ("Pending work", "pending_work"),
        ("Next steps", "next_steps"),
    )
    lines = [f"# {report['title']}", "", f"**Project:** {report['project']}", f"**Period:** {report['period_from']} to {report['period_to']}"]
    if report.get("responsible_person"):
        lines.append(f"**Responsible:** {report['responsible_person']}")
    for heading, key in headings:
        lines.extend(["", f"## {heading}"])
        values = report.get(key) or []
        lines.extend([f"- {value}" for value in values] or ["- None recorded"])
    evidence = report["evidence_summary"]
    lines.extend(["", "## Evidence coverage", f"- Coverage: {evidence['coverage']}", f"- Work items considered: {evidence['item_count']}"])
    return "\n".join(lines) + "\n"


def render_txt(report: dict) -> str:
    return render_markdown(report).replace("#### ", "").replace("### ", "").replace("## ", "").replace("# ", "").replace("**", "")


def render_json(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2) + "\n"


def render_pdf(report: dict, path: Path) -> None:
    """Render a simple local PDF without network calls or report-domain coupling."""
    from fpdf import FPDF

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 8, report["title"].encode("latin-1", "replace").decode("latin-1"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    label = f"Project: {report['project']}" if report.get("scope") != "workspace" else "Scope: Workspace"
    pdf.multi_cell(0, 6, f"{label}\nPeriod: {report['period_from']} to {report['period_to']}", new_x="LMARGIN", new_y="NEXT")
    sections = [("Executive summary", report["executive_summary"])]
    if report.get("scope") == "workspace":
        sections += [("Projects", [f"{project['project']}: {project['metrics']['work_items']} work item(s)" for project in report["projects"]]), ("Workspace results", report["workspace_results"]), ("Current blockers", report["workspace_blockers"]), ("Next priorities", report["workspace_next_priorities"])]
    else:
        sections += [("Completed work", report["completed_work"]), ("Major results", report["major_results"]), ("Validation", report["tests_and_validation"]), ("Pending work", report["pending_work"]), ("Next steps", report["next_steps"])]
    for heading, values in sections:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 7, heading, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=10)
        for value in values or ["None recorded"]:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 5, (f"- {value}").encode("latin-1", "replace").decode("latin-1"), new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(path))
