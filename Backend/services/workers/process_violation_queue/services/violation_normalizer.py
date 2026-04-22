from __future__ import annotations

from datetime import datetime, timezone

from services.common.config import load_settings
from services.common.plate import is_valid_plate, normalize_plate


def normalize_violation(payload: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    settings = load_settings()

    vehicle = payload.get("vehicle", {}) if isinstance(payload.get("vehicle"), dict) else {}
    confidence = float(vehicle.get("plate_ocr_confidence", 0.0) or 0.0)
    plate_number = normalize_plate(vehicle.get("plate_number"))
    plate_valid = bool(vehicle.get("plate_format_valid")) if "plate_format_valid" in vehicle else is_valid_plate(plate_number)

    review_reasons: list[str] = []
    if confidence < settings.min_ocr_confidence:
        review_reasons.append("low_ocr_confidence")
    if not plate_number:
        review_reasons.append("missing_plate")
    elif not plate_valid:
        review_reasons.append("invalid_plate_format")

    review_required = len(review_reasons) > 0
    status = "REQUIRES_REVIEW" if review_required else "CONFIRMED_AUTO"

    return {
        **payload,
        "vehicle": {
            **vehicle,
            "plate_number": plate_number,
            "plate_format_valid": plate_valid,
            "plate_ocr_confidence": confidence,
        },
        "violation_status": status,
        "review_required": review_required,
        "review_reason": ",".join(review_reasons) if review_required else None,
        "evidence_status": "READY",
        "created_at": now,
        "updated_at": now,
    }
