from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from services.common.config import load_settings
from services.workers.process_violation_queue.services.alert_publisher import publish_alert
from services.workers.process_violation_queue.services.challan_generator import generate_challan
from services.workers.process_violation_queue.services.gemini_vehicle_enricher import enrich_vehicle_attributes
from services.workers.process_violation_queue.services.violation_normalizer import normalize_violation
from services.workers.process_violation_queue.services.violation_persister import ViolationPersister


def _safe_float(raw: Any, fallback: float = 0.0) -> float:
    try:
        return float(raw)
    except Exception:
        return fallback


def process_violation_payload(payload: Dict[str, Any], persister: ViolationPersister) -> Dict[str, Any]:
    enrichment = enrich_vehicle_attributes(payload)
    vehicle = payload.get("vehicle", {}) if isinstance(payload.get("vehicle"), dict) else {}

    existing_confidence = _safe_float(vehicle.get("plate_ocr_confidence"), 0.0)
    enriched_confidence = _safe_float(enrichment.get("plate_confidence"), 0.0)
    selected_confidence = max(existing_confidence, enriched_confidence)

    detected_plate = str(enrichment.get("plate_number") or "").strip()
    merged_plate = str(vehicle.get("plate_number") or detected_plate).strip()

    payload["vehicle"] = {
        **vehicle,
        "plate_number": merged_plate,
        "plate_ocr_confidence": round(selected_confidence, 3),
        "detected_color": enrichment.get("vehicle_color"),
        "detected_type": enrichment.get("vehicle_type"),
    }
    payload["vehicle_enrichment"] = enrichment

    normalized = normalize_violation(payload)
    normalized["challan"] = generate_challan(normalized)
    persister.persist(normalized)
    publish_alert(normalized)
    return normalized


def process_queue_once() -> dict:
    settings = load_settings()
    queue_path: Path = settings.local_data_dir / "violation_queue.jsonl"

    if not queue_path.exists():
        return {"processed": 0}

    lines = queue_path.read_text(encoding="utf-8").splitlines()
    persister = ViolationPersister()
    processed = 0

    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        process_violation_payload(payload, persister)
        processed += 1

    queue_path.write_text("", encoding="utf-8")
    return {"processed": processed}


if __name__ == "__main__":
    result = process_queue_once()
    print(json.dumps(result))
