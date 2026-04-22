from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from services.ingest_api.app import app


TEST_IMAGE_BASE64 = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/w8AAgMBgM7Qx8YAAAAASUVORK5CYII="
)


def _sample_detect_payload() -> dict:
    return {
        "violation_type": "FOOTPATH_ENCROACHMENT",
        "timestamp": "2026-01-01T12:00:00Z",
        "image_base64": TEST_IMAGE_BASE64,
        "location": {
            "camera_id": "FP_CAM_001",
            "location_name": "Sample Junction",
            "gps_lat": 12.9716,
            "gps_lng": 77.5946,
        },
        "vehicle": {
            "plate_number": "KA05AB1234",
            "plate_ocr_confidence": 0.88,
            "vehicle_class": "motorcycle",
            "estimated_speed_kmph": 18.2,
        },
    }


def test_detect_violation_generates_challan_and_supports_idempotency():
    client = TestClient(app)
    idem = f"idem-{uuid.uuid4().hex[:12]}"

    first = client.post(
        "/detect-violation",
        headers={"x-api-key": "dev-key", "x-idempotency-key": idem},
        json=_sample_detect_payload(),
    )
    second = client.post(
        "/detect-violation",
        headers={"x-api-key": "dev-key", "x-idempotency-key": idem},
        json=_sample_detect_payload(),
    )

    assert first.status_code == 201
    payload = first.json()["data"]
    assert payload["duplicate"] is False
    assert payload["challan"]["challan_id"].startswith("CH-")
    assert payload["challan"]["plate_number"] == "KA05AB1234"

    assert second.status_code == 201
    second_payload = second.json()["data"]
    assert second_payload["duplicate"] is True


def test_generate_challan_endpoint_returns_structured_challan():
    client = TestClient(app)

    payload = {
        "violation_type": "FOOTPATH_ENCROACHMENT",
        "timestamp": "2026-01-01T12:30:00Z",
        "image_base64": TEST_IMAGE_BASE64,
        "location": {
            "camera_id": "FP_CAM_001",
            "location_name": "Sample Junction",
        },
        "vehicle": {
            "plate_number": "MH12DE1234",
            "vehicle_type": "bike",
            "vehicle_color": "black",
            "vehicle_class": "motorcycle",
            "plate_ocr_confidence": 0.9,
        },
    }

    response = client.post(
        "/generate-challan",
        headers={"x-api-key": "dev-key", "x-idempotency-key": f"idem-{uuid.uuid4().hex[:12]}"},
        json=payload,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    challan = data["challan"]
    assert data["duplicate"] is False
    assert challan["plate_number"] == "MH12DE1234"
    assert challan["vehicle_type"] in {"bike", "motorcycle"}
    assert challan["vehicle_color"] in {"black", "unknown"}
