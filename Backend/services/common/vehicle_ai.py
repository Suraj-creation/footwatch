from __future__ import annotations

import base64
import json
import re
from typing import Any, Dict, Optional
from urllib import error, request

from services.common.config import load_settings
from services.common.plate import normalize_plate


def _as_float(raw: Any, fallback: float) -> float:
    try:
        return float(raw)
    except Exception:
        return fallback


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _extract_json_object(raw_text: str) -> Optional[Dict[str, Any]]:
    text = raw_text.strip()
    if not text:
        return None

    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1)

    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except Exception:
        pass

    brace_match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not brace_match:
        return None

    try:
        value = json.loads(brace_match.group(0))
        if isinstance(value, dict):
            return value
    except Exception:
        return None

    return None


def _gemini_enrich(image_bytes: bytes) -> Optional[Dict[str, Any]]:
    settings = load_settings()
    api_key = settings.gemini_api_key.strip()
    if not api_key:
        return None

    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={api_key}"
    )
    image_b64 = base64.b64encode(image_bytes).decode("ascii")

    prompt = (
        "Analyze this traffic violation vehicle image and return ONLY compact JSON with keys: "
        "plate_number (string), plate_confidence (number 0-1), vehicle_type (string), "
        "vehicle_color (string), confidence (number 0-1), notes (string). "
        "Use empty string for unknown text values."
    )
    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": "image/jpeg", "data": image_b64}},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 256,
        },
    }

    req = request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    candidates = payload.get("candidates", [])
    if not candidates:
        return None

    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        return None

    raw_text = "".join(str(part.get("text", "")) for part in parts)
    parsed = _extract_json_object(raw_text)
    if not parsed:
        return None

    return {
        "plate_number": normalize_plate(str(parsed.get("plate_number", ""))),
        "plate_confidence": _clamp01(_as_float(parsed.get("plate_confidence", 0.0), 0.0)),
        "vehicle_type": str(parsed.get("vehicle_type", "")).strip().lower(),
        "vehicle_color": str(parsed.get("vehicle_color", "")).strip().lower(),
        "confidence": _clamp01(_as_float(parsed.get("confidence", 0.0), 0.0)),
        "notes": str(parsed.get("notes", "")).strip(),
        "source": "gemini",
    }


def _ocr_plate_fallback(image_bytes: Optional[bytes]) -> str:
    if not image_bytes:
        return ""

    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
        import pytesseract  # type: ignore
    except Exception:
        return ""

    try:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            return ""

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray, config="--psm 7")
        plate = normalize_plate(text)
        return plate if len(plate) >= 6 else ""
    except Exception:
        return ""


def extract_vehicle_attributes(
    image_bytes: Optional[bytes],
    vehicle_class: str = "",
    plate_hint: Optional[str] = None,
    color_hint: Optional[str] = None,
    type_hint: Optional[str] = None,
) -> Dict[str, Any]:
    ocr_plate = _ocr_plate_fallback(image_bytes)
    plate_fallback = normalize_plate(plate_hint) or ocr_plate
    vehicle_type_fallback = (
        str(type_hint or "").strip().lower()
        or str(vehicle_class or "").strip().lower()
        or "unknown"
    )
    vehicle_color_fallback = str(color_hint or "").strip().lower() or "unknown"

    fallback_plate_confidence = 0.0
    fallback_notes = "Gemini enrichment unavailable."
    if normalize_plate(plate_hint):
        fallback_plate_confidence = 0.5
    elif ocr_plate:
        fallback_plate_confidence = 0.45
        fallback_notes = "Gemini unavailable; fallback OCR used."

    fallback = {
        "plate_number": plate_fallback,
        "plate_confidence": fallback_plate_confidence,
        "vehicle_type": vehicle_type_fallback,
        "vehicle_color": vehicle_color_fallback,
        "confidence": 0.0,
        "notes": fallback_notes,
        "source": "fallback",
    }

    if not image_bytes:
        return fallback

    gemini_result = _gemini_enrich(image_bytes)
    if not gemini_result:
        return fallback

    plate = gemini_result.get("plate_number") or plate_fallback
    plate_conf = _clamp01(
        max(
            _as_float(gemini_result.get("plate_confidence", 0.0), 0.0),
            fallback["plate_confidence"],
        )
    )

    vehicle_type = gemini_result.get("vehicle_type") or vehicle_type_fallback
    vehicle_color = gemini_result.get("vehicle_color") or vehicle_color_fallback

    return {
        "plate_number": normalize_plate(str(plate)),
        "plate_confidence": plate_conf,
        "vehicle_type": str(vehicle_type).strip().lower() or "unknown",
        "vehicle_color": str(vehicle_color).strip().lower() or "unknown",
        "confidence": _clamp01(
            _as_float(gemini_result.get("confidence", plate_conf), plate_conf)
        ),
        "notes": str(gemini_result.get("notes", "")).strip(),
        "source": "gemini",
    }
