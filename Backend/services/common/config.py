from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    env: str
    region: str
    camera_state_table: str
    violations_table: str
    idempotency_table: str
    violation_queue_url: str
    evidence_bucket: str
    ingest_api_key: str
    gemini_api_key: str
    gemini_model: str
    min_ocr_confidence: float
    project_root: Path

    @property
    def local_data_dir(self) -> Path:
        directory = self.project_root / ".local"
        directory.mkdir(parents=True, exist_ok=True)
        return directory


def load_settings() -> Settings:
    def _as_float(raw: str, fallback: float) -> float:
        try:
            return float(raw)
        except Exception:
            return fallback

    root = Path(__file__).resolve().parents[2]
    return Settings(
        env=os.getenv("FW_ENV", "dev"),
        region=os.getenv("FW_REGION", "ap-south-1"),
        camera_state_table=os.getenv("FW_CAMERA_STATE_TABLE", "CameraLiveState"),
        violations_table=os.getenv("FW_VIOLATIONS_TABLE", "Violations"),
        idempotency_table=os.getenv("FW_IDEMPOTENCY_TABLE", "IdempotencyRecords"),
        violation_queue_url=os.getenv("FW_VIOLATION_QUEUE_URL", ""),
        evidence_bucket=os.getenv("FW_EVIDENCE_BUCKET", "footwatch-evidence"),
        ingest_api_key=os.getenv("FW_INGEST_API_KEY", "dev-key"),
        gemini_api_key=os.getenv("FW_GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", "")),
        gemini_model=os.getenv("FW_GEMINI_MODEL", "gemini-2.0-flash"),
        min_ocr_confidence=_as_float(os.getenv("FW_MIN_OCR_CONFIDENCE", "0.65"), 0.65),
        project_root=root,
    )
