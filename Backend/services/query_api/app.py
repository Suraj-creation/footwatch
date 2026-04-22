from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional
import zipfile

from fastapi import Body, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse

from services.common.errors import ApiError
from services.common.response import ok
from services.query_api.handlers.get_edge_config import handle_get_edge_config
from services.query_api.handlers.get_edge_runtime_status import handle_get_edge_runtime_status
from services.query_api.handlers.get_alerts import handle_get_alerts
from services.query_api.handlers.get_evidence_url import handle_get_evidence_url
from services.query_api.handlers.get_live_cameras import handle_get_live_cameras
from services.query_api.handlers.get_violation_details import handle_get_violation_details
from services.query_api.handlers.get_violations_summary import handle_get_violations_summary
from services.query_api.handlers.list_violations import handle_list_violations
from services.query_api.handlers.put_edge_config import handle_put_edge_config
from services.query_api.repositories.alerts_read_repo import AlertsReadRepository
from services.query_api.repositories.challans_read_repo import ChallansReadRepository
from services.query_api.repositories.edge_runtime_repo import EdgeRuntimeRepository
from services.query_api.repositories.evidence_repo import EvidenceRepository
from services.query_api.repositories.live_state_read_repo import LiveStateReadRepository
from services.query_api.repositories.violations_read_repo import ViolationsReadRepository

app = FastAPI(title="FootWatch Query API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

live_repo = LiveStateReadRepository()
violations_repo = ViolationsReadRepository()
challans_repo = ChallansReadRepository(violations_repo)
evidence_repo = EvidenceRepository()
alerts_repo = AlertsReadRepository()
edge_repo = EdgeRuntimeRepository()


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError):
    request_id = str(uuid.uuid4())
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict(request_id=request_id))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/live/cameras")
def get_live_cameras():
    request_id = str(uuid.uuid4())
    return ok(handle_get_live_cameras(live_repo), request_id)


@app.get("/v1/violations")
def list_violations(
    limit: int = Query(default=50, ge=1, le=200),
    camera_id: Optional[str] = Query(default=None),
    plate: Optional[str] = Query(default=None),
    vehicle_class: Optional[str] = Query(default=None, alias="class"),
    status: Optional[str] = Query(default=None),
    from_ts: Optional[str] = Query(default=None, alias="from"),
    to_ts: Optional[str] = Query(default=None, alias="to"),
):
    request_id = str(uuid.uuid4())
    filters = {
        key: value
        for key, value in {
            "camera_id": camera_id,
            "plate": plate,
            "class": vehicle_class,
            "status": status,
            "from": from_ts,
            "to": to_ts,
        }.items()
        if value is not None and value != ""
    }
    return ok(handle_list_violations(violations_repo, limit=limit, filters=filters), request_id)


@app.get("/v1/violations/summary")
def get_violations_summary():
    request_id = str(uuid.uuid4())
    return ok(handle_get_violations_summary(violations_repo), request_id)


@app.get("/v1/alerts")
def list_alerts(limit: int = Query(default=20, ge=1, le=100)):
    request_id = str(uuid.uuid4())
    return ok(handle_get_alerts(alerts_repo, limit=limit), request_id)


@app.get("/v1/violations/{violation_id}")
def get_violation_details(violation_id: str):
    request_id = str(uuid.uuid4())
    return ok(handle_get_violation_details(violations_repo, violation_id), request_id)


@app.get("/v1/violations/{violation_id}/evidence-url")
def get_evidence_url(violation_id: str, type: str = Query(default="full_frame")):
    request_id = str(uuid.uuid4())
    return ok(handle_get_evidence_url(evidence_repo, violations_repo, violation_id, type), request_id)


@app.get("/v1/challans")
@app.get("/challans")
def list_challans(
    limit: int = Query(default=50, ge=1, le=200),
    plate_number: Optional[str] = Query(default=None),
    challan_id: Optional[str] = Query(default=None),
    violation_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    camera_id: Optional[str] = Query(default=None),
    from_ts: Optional[str] = Query(default=None, alias="from"),
    to_ts: Optional[str] = Query(default=None, alias="to"),
):
    request_id = str(uuid.uuid4())
    filters = {
        key: value
        for key, value in {
            "plate_number": plate_number,
            "challan_id": challan_id,
            "violation_type": violation_type,
            "status": status,
            "camera_id": camera_id,
            "from": from_ts,
            "to": to_ts,
        }.items()
        if value is not None and value != ""
    }
    items = challans_repo.list_all(limit=limit, filters=filters)
    return ok({"items": items}, request_id)


@app.get("/v1/challan/{challan_id}")
@app.get("/challan/{challan_id}")
def get_challan(challan_id: str):
    request_id = str(uuid.uuid4())
    challan = challans_repo.by_id(challan_id)
    if not challan:
        raise ApiError(404, "challan_not_found", "Challan not found")
    return ok(challan, request_id)


@app.get("/v1/challan/{challan_id}/pdf")
@app.get("/challan/{challan_id}/pdf")
def download_challan_pdf(challan_id: str):
    challan = challans_repo.by_id(challan_id)
    if not challan:
        raise ApiError(404, "challan_not_found", "Challan not found")

    preferred_path = challan.get("pdf_path") or challan.get("html_path")
    if not isinstance(preferred_path, str) or not preferred_path:
        raise ApiError(404, "challan_not_found", "Challan file is unavailable")

    path = Path(preferred_path)
    if not path.exists():
        raise ApiError(404, "challan_not_found", "Challan file is unavailable")

    media_type = "application/pdf" if path.suffix.lower() == ".pdf" else "text/html"
    filename = f"{challan_id}{path.suffix.lower()}"
    return FileResponse(path=path, media_type=media_type, filename=filename)


@app.get("/v1/challan/{challan_id}/image")
@app.get("/challan/{challan_id}/image")
def get_challan_image(challan_id: str):
    challan = challans_repo.by_id(challan_id)
    if not challan:
        raise ApiError(404, "challan_not_found", "Challan not found")

    image_path = challan.get("image_url")
    if not isinstance(image_path, str) or not image_path:
        raise ApiError(404, "challan_image_not_found", "Challan image not available")

    path = Path(image_path)
    if not path.exists():
        raise ApiError(404, "challan_image_not_found", "Challan image not available")

    suffix = path.suffix.lower()
    media_type = "image/jpeg"
    if suffix == ".png":
        media_type = "image/png"
    elif suffix == ".webp":
        media_type = "image/webp"

    return FileResponse(path=path, media_type=media_type, filename=path.name)


@app.get("/v1/violations/{violation_id}/challan/download")
def download_violation_challan(violation_id: str):
    violation = violations_repo.by_id(violation_id)
    if not violation:
        raise ApiError(404, "not_found", "Violation not found")

    challan = violation.get("challan", {})
    preferred_path = challan.get("pdf_path") or challan.get("html_path")
    if not isinstance(preferred_path, str) or not preferred_path:
        raise ApiError(404, "challan_not_found", "Challan has not been generated yet")

    path = Path(preferred_path)
    if not path.exists():
        raise ApiError(404, "challan_not_found", "Challan file is unavailable")

    media_type = "application/pdf" if path.suffix.lower() == ".pdf" else "text/html"
    return FileResponse(
        path=path,
        media_type=media_type,
        filename=path.name,
    )


@app.get("/v1/challans/export")
def export_challans(
    from_ts: Optional[str] = Query(default=None, alias="from"),
    to_ts: Optional[str] = Query(default=None, alias="to"),
    camera_id: Optional[str] = Query(default=None),
):
    filters = {
        key: value
        for key, value in {
            "from": from_ts,
            "to": to_ts,
            "camera_id": camera_id,
        }.items()
        if value is not None and value != ""
    }
    items = violations_repo.list_all(limit=10_000, filters=filters)
    if not items:
        raise ApiError(404, "no_challans", "No violations matched the export filters")

    archive = BytesIO()
    exported = 0
    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for violation in items:
            violation_id = str(violation.get("violation_id", "unknown"))
            challan = violation.get("challan", {})
            path_str = challan.get("pdf_path") or challan.get("html_path")
            if not isinstance(path_str, str) or not path_str:
                continue
            path = Path(path_str)
            if not path.exists():
                continue
            ext = path.suffix.lower() or ".txt"
            archive_name = f"{violation_id}/challan{ext}"
            zf.write(path, arcname=archive_name)
            exported += 1

    if exported == 0:
        raise ApiError(404, "no_challans", "No generated challans were found for matched violations")

    archive.seek(0)
    return StreamingResponse(
        archive,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="footwatch_challans_export.zip"'},
    )


@app.get("/v1/edge/live-preview")
def get_edge_live_preview():
    request_id = str(uuid.uuid4())
    return ok(handle_get_edge_runtime_status(edge_repo), request_id)


@app.get("/v1/edge/live-preview/frame")
def get_edge_live_preview_frame():
    frame_bytes = edge_repo.get_preview_frame_bytes()
    if frame_bytes is None:
        raise ApiError(status_code=404, code="edge_preview_not_found", message="Edge preview frame not available")

    return Response(
        content=frame_bytes,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/v1/edge/config")
def get_edge_config():
    request_id = str(uuid.uuid4())
    return ok(handle_get_edge_config(edge_repo), request_id)


@app.put("/v1/edge/config")
def put_edge_config(payload: Dict[str, Any] = Body(default_factory=dict)):
    request_id = str(uuid.uuid4())
    return ok(handle_put_edge_config(edge_repo, payload), request_id)
