from __future__ import annotations

from typing import Any, Dict, Optional

from services.common.idempotency import payload_hash
from services.common.validators import validate_payload
from services.ingest_api.handlers.challan_pipeline import create_violation_challan_record
from services.ingest_api.repositories.idempotency_repo import IdempotencyRepository


def handle_post_detect_violation(
    payload: Dict[str, Any],
    idempotency_key: Optional[str],
    idempotency_repo: IdempotencyRepository,
) -> Dict[str, Any]:
    validate_payload(payload, "detect_violation_ingest.json")

    if idempotency_key and "violation_id" not in payload:
        payload["violation_id"] = f"det-{idempotency_key[:16]}"

    digest = payload_hash(payload)
    if idempotency_key and idempotency_repo.seen(idempotency_key, digest):
        return {
            "duplicate": True,
            "violation_id": payload.get("violation_id"),
            "challan": None,
        }

    record = create_violation_challan_record(payload, use_ai=True)

    if idempotency_key:
        idempotency_repo.remember(idempotency_key, digest)

    return {
        "duplicate": False,
        "violation_id": record.get("violation_id"),
        "challan": record.get("challan"),
        "status": record.get("violation_status"),
        "vehicle": record.get("vehicle"),
        "vehicle_enrichment": record.get("vehicle_enrichment"),
    }
