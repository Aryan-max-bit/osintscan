"""
Export search results to JSON and PDF reports.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.config import Config


def _ensure_exports_dir() -> Path:
    path = Path(Config.EXPORTS_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_json(
    username: str,
    results: list[dict[str, Any]],
    search_id: int | None = None,
) -> dict:
    """
    Write results to a JSON file and return metadata for the API response.
    """
    exports_dir = _ensure_exports_dir()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"osint_{username}_{timestamp}.json"
    filepath = exports_dir / filename

    payload = {
        "tool": "OSINT Username Finder",
        "username": username,
        "search_id": search_id,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "total": len(results),
            "found": sum(1 for r in results if r.get("status") == "found"),
            "not_found": sum(1 for r in results if r.get("status") == "not_found"),
            "errors": sum(1 for r in results if r.get("status") == "error"),
        },
        "results": results,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return {
        "filename": filename,
        "download_url": f"/api/export/download/{filename}",
        "format": "json",
    }


def export_pdf(
    username: str,
    results: list[dict[str, Any]],
    search_id: int | None = None,
) -> dict:
    """
    Generate a PDF report with summary table and found profiles.
    """
    exports_dir = _ensure_exports_dir()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"osint_{username}_{timestamp}.pdf"
    filepath = exports_dir / filename

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        textColor=colors.HexColor("#00ff88"),
        fontSize=18,
        spaceAfter=12,
    )
    body_style = styles["Normal"]

    found = [r for r in results if r.get("status") == "found"]
    not_found = sum(1 for r in results if r.get("status") == "not_found")
    errors = sum(1 for r in results if r.get("status") == "error")

    story = [
        Paragraph("OSINT Username Finder — Report", title_style),
        Paragraph(f"<b>Username:</b> {username}", body_style),
        Paragraph(
            f"<b>Exported:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            body_style,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph(
            f"Total sites: {len(results)} | Found: {len(found)} | "
            f"Not found: {not_found} | Errors: {errors}",
            body_style,
        ),
        Spacer(1, 0.3 * inch),
        Paragraph("<b>Found Profiles</b>", styles["Heading2"]),
        Spacer(1, 0.1 * inch),
    ]

    if found:
        table_data = [["Platform", "URL", "Response (ms)"]]
        for r in found:
            table_data.append([
                r.get("site_name", ""),
                r.get("url", "")[:60] + ("..." if len(r.get("url", "")) > 60 else ""),
                str(r.get("response_time_ms", "")),
            ])
        table = Table(table_data, colWidths=[1.5 * inch, 4 * inch, 1 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
                ]
            )
        )
        story.append(table)
    else:
        story.append(Paragraph("No profiles found.", body_style))

    doc.build(story)

    return {
        "filename": filename,
        "download_url": f"/api/export/download/{filename}",
        "format": "pdf",
    }
