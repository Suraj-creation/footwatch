from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from services.query_api.repositories.violations_read_repo import ViolationsReadRepository


class ChallansReadRepository:
    def __init__(self, violations_repo: ViolationsReadRepository) -> None:
        self._violations_repo = violations_repo

    def _safe_int(self, raw: Any, fallback: int) -> int:
        try:
            return int(raw)
        except Exception:
            return fallback

    def _safe_float(self, raw: Any, fallback: float) -> float:
        try:
            return float(raw)
        except Exception:
            return fallback

    def _map_violation_to_challan(self, violation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        challan = violation.get("challan", {}) if isinstance(violation.get("challan"), dict) else {}
        challan_id = str(challan.get("challan_id", "")).strip()
        if not challan_id:
            return None

        vehicle = violation.get("vehicle", {}) if isinstance(violation.get("vehicle"), dict) else {}
        location = violation.get("location", {}) if isinstance(violation.get("location"), dict) else {}
        evidence = violation.get("evidence", {}) if isinstance(violation.get("evidence"), dict) else {}

        pdf_path = str(challan.get("pdf_path", "")).strip()
        html_path = str(challan.get("html_path", "")).strip()
        image_url = str(challan.get("image_url") or evidence.get("full_frame") or evidence.get("vehicle_crop") or "").strip()

        pdf_available = bool(pdf_path and Path(pdf_path).exists())

        return {
            "challan_id": challan_id,
            "violation_id": str(challan.get("violation_id") or violation.get("violation_id") or "").strip(),
            "plate_number": str(challan.get("plate_number") or vehicle.get("plate_number") or "").strip(),
            "vehicle_type": str(challan.get("vehicle_type") or vehicle.get("detected_type") or vehicle.get("vehicle_class") or "unknown").strip(),
            "vehicle_color": str(challan.get("vehicle_color") or vehicle.get("detected_color") or "unknown").strip(),
            "violation_type": str(challan.get("violation_type") or violation.get("violation_type") or "FOOTPATH_ENCROACHMENT").strip(),
            "timestamp": str(challan.get("timestamp") or violation.get("timestamp") or "").strip(),
            "image_url": image_url,
            "fine_amount": self._safe_int(challan.get("fine_amount") or violation.get("fine_amount_inr") or 500, 500),
            "status": str(challan.get("status") or "GENERATED").strip(),
            "camera_id": str(challan.get("camera_id") or location.get("camera_id") or "").strip(),
            "location_name": str(challan.get("location_name") or location.get("location_name") or "").strip(),
            "plate_ocr_confidence": self._safe_float(challan.get("plate_ocr_confidence") or vehicle.get("plate_ocr_confidence") or 0.0, 0.0),
            "pdf_generated": bool(challan.get("pdf_generated") or pdf_available),
            "pdf_path": pdf_path,
            "html_path": html_path,
            "generated_at": str(challan.get("generated_at") or "").strip(),
            "pdf_endpoint": f"/v1/challan/{challan_id}/pdf",
            "image_endpoint": f"/v1/challan/{challan_id}/image",
        }

    def _load_all(self) -> List[Dict[str, Any]]:
        # Include all known violations; challan mapping filters only rows with challan payload.
        violations = self._violations_repo.list_all(limit=10_000, filters=None)
        items: List[Dict[str, Any]] = []
        for violation in violations:
            mapped = self._map_violation_to_challan(violation)
            if mapped:
                items.append(mapped)

        items.sort(key=lambda value: value.get("timestamp", ""), reverse=True)
        return items

    def list_all(self, limit: int = 50, filters: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        items = self._load_all()

        if filters:
            challan_id = filters.get("challan_id")
            plate_number = filters.get("plate_number")
            violation_type = filters.get("violation_type")
            from_ts = filters.get("from")
            to_ts = filters.get("to")
            status = filters.get("status")
            camera_id = filters.get("camera_id")

            def matches(item: Dict[str, Any]) -> bool:
                if challan_id and challan_id.upper() not in str(item.get("challan_id", "")).upper():
                    return False
                if plate_number and plate_number.upper() not in str(item.get("plate_number", "")).upper():
                    return False
                if violation_type and str(item.get("violation_type", "")).lower() != violation_type.lower():
                    return False
                if status and str(item.get("status", "")).lower() != status.lower():
                    return False
                if camera_id and str(item.get("camera_id", "")) != camera_id:
                    return False

                ts = str(item.get("timestamp", ""))
                if from_ts and ts < from_ts:
                    return False
                if to_ts and ts > to_ts:
                    return False

                return True

            items = [item for item in items if matches(item)]

        return items[:limit]

    def by_id(self, challan_id: str) -> Optional[Dict[str, Any]]:
        needle = challan_id.strip().upper()
        for item in self._load_all():
            if str(item.get("challan_id", "")).upper() == needle:
                return item
        return None
