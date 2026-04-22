from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from services.common.config import load_settings
from services.query_api.app import app


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDATx\x9cc``\xf8\xff\x1f\x00\x03\x03\x02\x00\xef\x89\x82\x9d\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _seed_challan_violation() -> tuple[str, str]:
    settings = load_settings()
    local_dir = settings.local_data_dir

    test_dir = local_dir / "test_challan_assets"
    test_dir.mkdir(parents=True, exist_ok=True)

    suffix = uuid.uuid4().hex[:10]
    violation_id = f"vio-challan-{suffix}"
    challan_id = f"CH-20260101-{suffix.upper()}"

    pdf_path = test_dir / f"{challan_id}.pdf"
    html_path = test_dir / f"{challan_id}.html"
    image_path = test_dir / f"{challan_id}.png"

    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n")
    html_path.write_text("<html><body>challan</body></html>", encoding="utf-8")
    image_path.write_bytes(PNG_BYTES)

    record = {
        "violation_id": violation_id,
        "timestamp": "2026-01-01T12:00:00Z",
        "violation_type": "FOOTPATH_ENCROACHMENT",
        "violation_status": "CONFIRMED_AUTO",
        "location": {
            "camera_id": "FP_CAM_001",
            "location_name": "Sample Junction",
        },
        "vehicle": {
            "plate_number": "KA09ZZ9999",
            "vehicle_class": "motorcycle",
            "detected_type": "bike",
            "detected_color": "black",
            "plate_ocr_confidence": 0.9,
            "estimated_speed_kmph": 19.1,
        },
        "evidence": {
            "full_frame": str(image_path),
        },
        "fine_amount_inr": 500,
        "challan": {
            "challan_id": challan_id,
            "violation_id": violation_id,
            "plate_number": "KA09ZZ9999",
            "vehicle_type": "bike",
            "vehicle_color": "black",
            "violation_type": "FOOTPATH_ENCROACHMENT",
            "timestamp": "2026-01-01T12:00:00Z",
            "image_url": str(image_path),
            "fine_amount": 500,
            "status": "GENERATED",
            "generated_at": "2026-01-01T12:00:01Z",
            "pdf_path": str(pdf_path),
            "html_path": str(html_path),
            "pdf_generated": True,
        },
    }

    violations_path = local_dir / "violations.jsonl"
    with violations_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")

    return challan_id, violation_id


def test_list_and_get_challan_endpoints():
    challan_id, _ = _seed_challan_violation()
    client = TestClient(app)

    list_resp = client.get("/v1/challans?plate_number=KA09ZZ9999")
    assert list_resp.status_code == 200
    items = list_resp.json()["data"]["items"]
    assert any(item["challan_id"] == challan_id for item in items)

    detail_resp = client.get(f"/v1/challan/{challan_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["challan_id"] == challan_id
    assert detail["plate_number"] == "KA09ZZ9999"


def test_challan_pdf_and_image_download_endpoints():
    challan_id, _ = _seed_challan_violation()
    client = TestClient(app)

    pdf_resp = client.get(f"/v1/challan/{challan_id}/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"].startswith("application/pdf")

    img_resp = client.get(f"/v1/challan/{challan_id}/image")
    assert img_resp.status_code == 200
    assert img_resp.headers["content-type"].startswith("image/")
