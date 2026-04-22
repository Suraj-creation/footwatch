from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from services.common.config import load_settings
from services.common.plate import normalize_plate

try:
    from fpdf import FPDF
except Exception:  # pragma: no cover - optional runtime dependency
    FPDF = None


_FINE_BY_TYPE = {
    "FOOTPATH_ENCROACHMENT": 500,
    "SIGNAL_VIOLATION": 1000,
    "NO_HELMET": 1000,
}


def _as_float(raw: Any, fallback: float) -> float:
    try:
        return float(raw)
    except Exception:
        return fallback


def _read_challan_rows(path: Path) -> list[Dict[str, Any]]:
    if not path.exists():
        return []

    rows: list[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except Exception:
                continue
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _write_challan_rows(path: Path, rows: list[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _resolve_fine_amount(violation: Dict[str, Any], violation_type: str) -> int:
    raw = violation.get("fine_amount_inr", violation.get("fine_amount"))
    if isinstance(raw, (int, float)):
        return max(0, int(raw))
    return _FINE_BY_TYPE.get(violation_type, 500)


def _challan_id_for_violation(violation_id: str, now: datetime) -> str:
    token = hashlib.sha1(violation_id.encode("utf-8")).hexdigest()[:8].upper()
    return f"CH-{now.strftime('%Y%m%d')}-{token}"


def _challan_html(challan: Dict[str, Any], violation: Dict[str, Any]) -> str:
    vehicle = violation.get("vehicle", {})
    location = violation.get("location", {})
    enrichment = violation.get("vehicle_enrichment", {})
    evidence = violation.get("evidence", {})
    return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>e-Challan {challan["challan_id"]}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 24px; color: #111; }}
      h1 {{ margin-bottom: 8px; }}
      .muted {{ color: #666; font-size: 12px; }}
      table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
      td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
      td:first-child {{ width: 260px; font-weight: bold; background: #fafafa; }}
    </style>
  </head>
  <body>
    <h1>FootWatch e-Challan</h1>
    <div class="muted">Generated at {challan["generated_at"]}</div>
    <table>
      <tr><td>Challan ID</td><td>{challan["challan_id"]}</td></tr>
      <tr><td>Violation ID</td><td>{violation.get("violation_id", "N/A")}</td></tr>
            <tr><td>Violation Type</td><td>{challan.get("violation_type", "N/A")}</td></tr>
      <tr><td>Timestamp</td><td>{violation.get("timestamp", "N/A")}</td></tr>
            <tr><td>Plate Number</td><td>{challan.get("plate_number", "N/A")}</td></tr>
            <tr><td>Vehicle Type</td><td>{challan.get("vehicle_type", "N/A")}</td></tr>
            <tr><td>Vehicle Color</td><td>{challan.get("vehicle_color", "N/A")}</td></tr>
            <tr><td>Vehicle Class</td><td>{vehicle.get("vehicle_class", "N/A")}</td></tr>
      <tr><td>Estimated Speed (km/h)</td><td>{vehicle.get("estimated_speed_kmph", "N/A")}</td></tr>
      <tr><td>Detected Color</td><td>{enrichment.get("vehicle_color", "unknown")}</td></tr>
      <tr><td>Detected Type</td><td>{enrichment.get("vehicle_type", "unknown")}</td></tr>
      <tr><td>AI Enrichment Source</td><td>{enrichment.get("source", "fallback")}</td></tr>
      <tr><td>OCR Confidence</td><td>{vehicle.get("plate_ocr_confidence", "N/A")}</td></tr>
      <tr><td>Camera ID</td><td>{location.get("camera_id", "N/A")}</td></tr>
      <tr><td>Location</td><td>{location.get("location_name", "N/A")}</td></tr>
            <tr><td>Fine (INR)</td><td>{challan.get("fine_amount", 500)}</td></tr>
            <tr><td>Status</td><td>{challan.get("status", "N/A")}</td></tr>
      <tr><td>Full Frame Evidence</td><td>{evidence.get("full_frame", "N/A")}</td></tr>
      <tr><td>Vehicle Crop Evidence</td><td>{evidence.get("vehicle_crop", "N/A")}</td></tr>
      <tr><td>Plate Crop Evidence</td><td>{evidence.get("plate_crop_enhanced", "N/A")}</td></tr>
            <tr><td>Violation Status</td><td>{violation.get("violation_status", "N/A")}</td></tr>
    </table>
  </body>
</html>
"""


def _write_challan_pdf(path: Path, challan: Dict[str, Any], violation: Dict[str, Any]) -> bool:
    if FPDF is None:
        return False

    vehicle = violation.get("vehicle", {})
    location = violation.get("location", {})
    enrichment = violation.get("vehicle_enrichment", {})
    evidence = violation.get("evidence", {})
    rows = [
        ("Challan ID", challan.get("challan_id", "N/A")),
        ("Violation ID", violation.get("violation_id", "N/A")),
        ("Violation Type", challan.get("violation_type", "N/A")),
        ("Timestamp", violation.get("timestamp", "N/A")),
        ("Plate Number", challan.get("plate_number", "N/A")),
        ("Vehicle Type", challan.get("vehicle_type", "N/A")),
        ("Vehicle Color", challan.get("vehicle_color", "N/A")),
        ("Vehicle Class", vehicle.get("vehicle_class", "N/A")),
        ("Estimated Speed (km/h)", vehicle.get("estimated_speed_kmph", "N/A")),
        ("Detected Color", enrichment.get("vehicle_color", "unknown")),
        ("Detected Type", enrichment.get("vehicle_type", "unknown")),
        ("AI Enrichment Source", enrichment.get("source", "fallback")),
        ("OCR Confidence", vehicle.get("plate_ocr_confidence", "N/A")),
        ("Camera ID", location.get("camera_id", "N/A")),
        ("Location", location.get("location_name", "N/A")),
        ("Fine (INR)", challan.get("fine_amount", 500)),
        ("Status", challan.get("status", "N/A")),
        ("Full Frame Evidence", evidence.get("full_frame", "N/A")),
        ("Vehicle Crop Evidence", evidence.get("vehicle_crop", "N/A")),
        ("Plate Crop Evidence", evidence.get("plate_crop_enhanced", "N/A")),
        ("Violation Status", violation.get("violation_status", "N/A")),
    ]

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "FootWatch e-Challan", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"Generated at {challan.get('generated_at', 'N/A')}", ln=1)
    pdf.ln(3)

    for key, value in rows:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(58, 7, f"{key}:")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 7, str(value), wrapmode="CHAR")

    pdf.output(str(path))
    return True


def generate_challan(violation: Dict[str, Any]) -> Dict[str, Any]:
    settings = load_settings()
    challans_dir = settings.local_data_dir / "challans"
    challans_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc)
    violation_id = str(violation.get("violation_id", "unknown"))
    json_path = challans_dir / "challans.jsonl"
    existing_rows = _read_challan_rows(json_path)

    existing = next((row for row in existing_rows if str(row.get("violation_id", "")) == violation_id), None)
    challan_id = str(existing.get("challan_id")) if isinstance(existing, dict) and existing.get("challan_id") else _challan_id_for_violation(violation_id, ts)

    html_path = challans_dir / f"{challan_id}.html"
    pdf_path = challans_dir / f"{challan_id}.pdf"

    vehicle = violation.get("vehicle", {}) if isinstance(violation.get("vehicle"), dict) else {}
    enrichment = violation.get("vehicle_enrichment", {}) if isinstance(violation.get("vehicle_enrichment"), dict) else {}
    location = violation.get("location", {}) if isinstance(violation.get("location"), dict) else {}
    evidence = violation.get("evidence", {}) if isinstance(violation.get("evidence"), dict) else {}

    plate_number = normalize_plate(vehicle.get("plate_number"))
    vehicle_type = (
        str(vehicle.get("detected_type") or enrichment.get("vehicle_type") or vehicle.get("vehicle_class") or "unknown")
        .strip()
        .lower()
    )
    vehicle_color = str(vehicle.get("detected_color") or enrichment.get("vehicle_color") or "unknown").strip().lower()
    violation_type = str(violation.get("violation_type") or "FOOTPATH_ENCROACHMENT").strip().upper()
    timestamp = str(violation.get("timestamp") or ts.isoformat())
    image_url = str(evidence.get("full_frame") or evidence.get("vehicle_crop") or "")
    fine_amount = _resolve_fine_amount(violation, violation_type)
    status = "REQUIRES_REVIEW" if bool(violation.get("review_required", False)) else "GENERATED"

    challan = {
        "challan_id": challan_id,
        "violation_id": violation_id,
        "plate_number": plate_number,
        "vehicle_type": vehicle_type,
        "vehicle_color": vehicle_color,
        "violation_type": violation_type,
        "timestamp": timestamp,
        "image_url": image_url,
        "fine_amount": fine_amount,
        "generated_at": ts.isoformat(),
        "camera_id": location.get("camera_id"),
        "location_name": location.get("location_name"),
        "status": status,
        "html_path": str(html_path),
        "pdf_path": str(pdf_path),
        "pdf_generated": False,
        "plate_ocr_confidence": round(_as_float(vehicle.get("plate_ocr_confidence"), 0.0), 3),
    }

    html_path.write_text(_challan_html(challan, violation), encoding="utf-8")
    challan["pdf_generated"] = _write_challan_pdf(pdf_path, challan, violation)
    if not challan["pdf_generated"] and pdf_path.exists():
        pdf_path.unlink(missing_ok=True)
    if not challan["pdf_generated"] and challan["status"] == "GENERATED":
        challan["status"] = "GENERATED_HTML_ONLY"

    next_rows = [
        row
        for row in existing_rows
        if str(row.get("violation_id", "")) != violation_id and str(row.get("challan_id", "")) != challan_id
    ]
    next_rows.append(challan)
    _write_challan_rows(json_path, next_rows)

    return challan
