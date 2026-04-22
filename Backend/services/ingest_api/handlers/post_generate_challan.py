from __future__ import annotations

from typing import Any, Dict, Optional

from services.common.idempotency import payload_hash
from services.common.validators import validate_payload
from services.ingest_api.handlers.challan_pipeline import create_violation_challan_record
from services.ingest_api.repositories.idempotency_repo import IdempotencyRepository


def handle_post_generate_challan(
    payload: Dict[str, Any],
    idempotency_key: Optional[str],
    idempotency_repo: IdempotencyRepository,
) -> Dict[str, Any]:
    validate_payload(payload, "generate_challan_ingest.json")

    if idempotency_key and "violation_id" not in payload:
        payload["violation_id"] = f"gen-{idempotency_key[:16]}"

    vehicle = payload.get("vehicle", {}) if isinstance(payload.get("vehicle"), dict) else {}
    if "plate_ocr_confidence" not in vehicle:
        payload["vehicle"] = {
            **vehicle,
            "plate_ocr_confidence": 0.8,
        }

    digest = payload_hash(payload)
    if idempotency_key and idempotency_repo.seen(idempotency_key, digest):
        return {
            "duplicate": True,
            "violation_id": payload.get("violation_id"),
            "challan": None,
        }

    record = create_violation_challan_record(payload, use_ai=False)

    if idempotency_key:
        idempotency_repo.remember(idempotency_key, digest)

    return {
        "duplicate": False,
        "violation_id": record.get("violation_id"),
        "challan": record.get("challan"),
        "status": record.get("violation_status"),
        "vehicle": record.get("vehicle"),
    }
