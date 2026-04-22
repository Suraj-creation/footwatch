from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

from services.common.config import load_settings
from services.common.plate import is_valid_plate, normalize_plate
from services.common.vehicle_ai import extract_vehicle_attributes
from services.workers.process_violation_queue.services.alert_publisher import publish_alert
from services.workers.process_violation_queue.services.challan_generator import generate_challan
from services.workers.process_violation_queue.services.violation_normalizer import normalize_violation
from services.workers.process_violation_queue.services.violation_persister import ViolationPersister


def _safe_float(raw: Any, fallback: float = 0.0) -> float:
    try:
        return float(raw)
    except Exception:
        return fallback


def _safe_int(raw: Any, fallback: int = 0) -> int:
    try:
        return int(raw)
    except Exception:
        return fallback


def _decode_image_base64(image_base64: str) -> Tuple[bytes, str]:
    payload = image_base64.strip()
    ext = ".jpg"

    if payload.startswith("data:") and "," in payload:
        header, encoded = payload.split(",", 1)
        payload = encoded
        if "image/png" in header:
            ext = ".png"
        elif "image/webp" in header:
            ext = ".webp"

    try:
        decoded = base64.b64decode(payload, validate=True)
    except Exception as exc:
        raise ValueError("Invalid image_base64 payload") from exc
    if not decoded:
        raise ValueError("Image payload is empty")
    return decoded, ext


def _resolve_image(payload: Dict[str, Any], violation_id: str) -> Tuple[bytes, Dict[str, str]]:
    settings = load_settings()
    evidence_dir = settings.local_data_dir / "evidence" / violation_id
    evidence_dir.mkdir(parents=True, exist_ok=True)

    image_bytes: bytes
    ext = ".jpg"

    image_base64 = payload.get("image_base64")
    image_path = payload.get("image_path")

    if isinstance(image_base64, str) and image_base64.strip():
        image_bytes, ext = _decode_image_base64(image_base64)
    elif isinstance(image_path, str) and image_path.strip():
        source = Path(image_path)
        if not source.exists() or not source.is_file():
            raise ValueError("Provided image_path does not exist")
        image_bytes = source.read_bytes()
        if source.suffix:
            ext = source.suffix.lower()
    else:
        raise ValueError("Either image_base64 or image_path is required")

    full_frame_path = evidence_dir / f"full_frame{ext}"
    full_frame_path.write_bytes(image_bytes)

    evidence = {
        "full_frame": str(full_frame_path.resolve()),
    }

    if isinstance(image_path, str) and image_path.strip() and Path(image_path).exists():
        evidence["source_image"] = str(Path(image_path).resolve())

    return image_bytes, evidence


def _location_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    location = payload.get("location", {}) if isinstance(payload.get("location"), dict) else {}

    camera_id = str(location.get("camera_id") or payload.get("camera_id") or "FP_CAM_001").strip()
    location_name = str(location.get("location_name") or payload.get("location_name") or "Unknown Location").strip()

    gps_lat_raw = location.get("gps_lat", payload.get("gps_lat", 0.0))
    gps_lng_raw = location.get("gps_lng", payload.get("gps_lng", 0.0))

    return {
        "camera_id": camera_id,
        "location_name": location_name,
        "gps_lat": _safe_float(gps_lat_raw, 0.0),
        "gps_lng": _safe_float(gps_lng_raw, 0.0),
    }


def create_violation_challan_record(payload: Dict[str, Any], use_ai: bool = True) -> Dict[str, Any]:
    violation_id = str(payload.get("violation_id") or f"vio-{uuid.uuid4().hex[:16]}")
    timestamp = str(payload.get("timestamp") or datetime.now(timezone.utc).isoformat())

    image_bytes, evidence = _resolve_image(payload, violation_id)
    location = _location_from_payload(payload)

    vehicle_input = payload.get("vehicle", {}) if isinstance(payload.get("vehicle"), dict) else {}

    vehicle_class_hint = str(
        vehicle_input.get("vehicle_class")
        or vehicle_input.get("vehicle_type")
        or vehicle_input.get("detected_type")
        or "unknown"
    ).strip().lower()

    enrichment = extract_vehicle_attributes(
        image_bytes=image_bytes if use_ai else None,
        vehicle_class=vehicle_class_hint,
        plate_hint=vehicle_input.get("plate_number"),
        color_hint=vehicle_input.get("vehicle_color") or vehicle_input.get("detected_color"),
        type_hint=vehicle_input.get("vehicle_type") or vehicle_input.get("detected_type") or vehicle_input.get("vehicle_class"),
    )

    plate_number = normalize_plate(vehicle_input.get("plate_number") or enrichment.get("plate_number"))
    plate_confidence = max(
        _safe_float(vehicle_input.get("plate_ocr_confidence"), 0.0),
        _safe_float(enrichment.get("plate_confidence"), 0.0),
    )

    detected_type = str(
        vehicle_input.get("vehicle_type")
        or vehicle_input.get("detected_type")
        or enrichment.get("vehicle_type")
        or vehicle_class_hint
        or "unknown"
    ).strip().lower()
    detected_color = str(
        vehicle_input.get("vehicle_color")
        or vehicle_input.get("detected_color")
        or enrichment.get("vehicle_color")
        or "unknown"
    ).strip().lower()
    track_id = _safe_int(vehicle_input.get("track_id"), -1)

    violation = {
        "violation_id": violation_id,
        "timestamp": timestamp,
        "location": location,
        "vehicle": {
            "plate_number": plate_number,
            "plate_ocr_confidence": round(plate_confidence, 3),
            "plate_format_valid": is_valid_plate(plate_number),
            "vehicle_class": vehicle_class_hint,
            "estimated_speed_kmph": _safe_float(vehicle_input.get("estimated_speed_kmph"), 0.0),
            "track_id": track_id if track_id >= 0 else None,
            "detected_color": detected_color,
            "detected_type": detected_type,
        },
        "vehicle_enrichment": enrichment,
        "violation_type": str(payload.get("violation_type") or "FOOTPATH_ENCROACHMENT").strip().upper(),
        "fine_amount_inr": _safe_int(payload.get("fine_amount_inr", payload.get("fine_amount", 500)), 500),
        "evidence": evidence,
    }

    if "context" in payload:
        violation["context"] = payload.get("context")

    normalized = normalize_violation(violation)
    normalized["challan"] = generate_challan(normalized)

    persister = ViolationPersister()
    persister.persist(normalized)
    publish_alert(normalized)

    return normalized
