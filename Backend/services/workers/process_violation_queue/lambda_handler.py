from __future__ import annotations

import json
from typing import Any, Dict, List

from services.workers.process_violation_queue.handler import process_queue_once, process_violation_payload
from services.workers.process_violation_queue.services.violation_persister import ViolationPersister


def _process_records(records: List[Dict[str, Any]]) -> int:
    persister = ViolationPersister()
    processed = 0

    for record in records:
        raw_body = record.get("body")
        if raw_body is None:
            continue

        try:
            payload = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        process_violation_payload(payload, persister)
        processed += 1

    return processed


def handler(event: Dict[str, Any], _context: Any) -> Dict[str, int]:
    records = event.get("Records", []) if isinstance(event, dict) else []

    if records:
        return {"processed": _process_records(records)}

    return process_queue_once()
