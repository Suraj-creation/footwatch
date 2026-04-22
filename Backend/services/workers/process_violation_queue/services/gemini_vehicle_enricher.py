from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from services.common.vehicle_ai import extract_vehicle_attributes


def _read_evidence_bytes(payload: Dict[str, Any]) -> Optional[bytes]:
    evidence = payload.get("evidence", {}) if isinstance(payload.get("evidence"), dict) else {}
    image_path = evidence.get("vehicle_crop") or evidence.get("full_frame")
    if not isinstance(image_path, str) or not image_path.strip():
        return None

    try:
        return Path(image_path).read_bytes()
    except Exception:
        return None


def enrich_vehicle_attributes(payload: Dict[str, Any]) -> Dict[str, Any]:
    vehicle = payload.get("vehicle", {}) if isinstance(payload.get("vehicle"), dict) else {}
    return extract_vehicle_attributes(
        image_bytes=_read_evidence_bytes(payload),
        vehicle_class=str(vehicle.get("vehicle_class", "")).strip().lower(),
        plate_hint=vehicle.get("plate_number"),
        color_hint=vehicle.get("detected_color") or vehicle.get("vehicle_color"),
        type_hint=vehicle.get("detected_type") or vehicle.get("vehicle_type"),
    )
