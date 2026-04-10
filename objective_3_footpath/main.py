from __future__ import annotations

import argparse
import json
import re
import time
from collections import defaultdict, deque
from pathlib import Path

import cv2
import numpy as np
from paddleocr import PaddleOCR
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PROJECT_ROOT / "config"
MODELS_DIR = PROJECT_ROOT / "models"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_plate(text: str) -> bool:
    pattern = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$")
    bh_pattern = re.compile(r"^[0-9]{2}BH[0-9]{4}[A-Z]{2}$")
    return bool(pattern.match(text) or bh_pattern.match(text))


def enhance_plate_cpu(plate_img: np.ndarray) -> np.ndarray:
    target_w = max(400, plate_img.shape[1] * 3)
    scale = target_w / max(plate_img.shape[1], 1)
    new_h = max(32, int(plate_img.shape[0] * scale))
    up = cv2.resize(plate_img, (target_w, new_h), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    eq = clahe.apply(gray)
    blur = cv2.GaussianBlur(eq, (0, 0), 1.5)
    sharp = cv2.addWeighted(eq, 1.8, blur, -0.8, 0)
    denoised = cv2.bilateralFilter(sharp, 5, 40, 40)
    return cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)


def clean_plate_text(raw: str) -> str:
    text = raw.upper().replace(" ", "").replace("-", "").replace(".", "")
    return re.sub(r"[^A-Z0-9]", "", text)


def run_smoke(video_source: str | int = 0, max_frames: int = 60) -> None:
    speed_cfg = load_json(CONFIG_DIR / "speed_calibration.json")
    ppm = float(speed_cfg.get("pixels_per_metre", 47.0))
    fps_cfg = float(speed_cfg.get("camera_fps", 15.0))

    two_wheeler_model = YOLO(str(MODELS_DIR / "twowheeler_yolov8n.pt"))
    lp_model = YOLO(str(MODELS_DIR / "lp_localiser.pt"))
    ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)

    track_hist: dict[int, deque[tuple[int, int]]] = defaultdict(lambda: deque(maxlen=10))

    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open source: {video_source}")

    print("Starting smoke run...")
    frame_count = 0

    while frame_count < max_frames:
        ok, frame = cap.read()
        if not ok:
            break

        frame_count += 1
        t0 = time.time()

        results = two_wheeler_model.track(frame, persist=True, tracker="bytetrack.yaml", conf=0.45, verbose=False)
        if results and results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            ids = results[0].boxes.id.cpu().numpy().astype(int)

            for bbox, track_id in zip(boxes, ids):
                x1, y1, x2, y2 = bbox
                center = ((x1 + x2) // 2, (y1 + y2) // 2)
                track_hist[track_id].append(center)

                if len(track_hist[track_id]) >= 3:
                    p1 = np.array(track_hist[track_id][-2], dtype=np.float32)
                    p2 = np.array(track_hist[track_id][-1], dtype=np.float32)
                    speed = float(np.linalg.norm(p2 - p1) / max(ppm, 1e-6) * fps_cfg * 3.6)
                else:
                    speed = 0.0

                if speed < 5.0:
                    continue

                crop = frame[max(0, y1):max(1, y2), max(0, x1):max(1, x2)]
                if crop.size == 0:
                    continue

                lp_results = lp_model(crop, conf=0.3, verbose=False)
                if not lp_results or len(lp_results[0].boxes) == 0:
                    continue

                lp_boxes = lp_results[0].boxes.xyxy.cpu().numpy().astype(int)
                lx1, ly1, lx2, ly2 = lp_boxes[0]
                plate = crop[max(0, ly1):max(1, ly2), max(0, lx1):max(1, lx2)]
                if plate.size == 0:
                    continue

                enhanced = enhance_plate_cpu(plate)
                text_result = ocr.ocr(enhanced, cls=True)
                if text_result and text_result[0]:
                    raw = "".join([line[1][0] for line in text_result[0]])
                    cleaned = clean_plate_text(raw)
                    is_valid = validate_plate(cleaned)
                    print(f"frame={frame_count} track={track_id} speed={speed:.1f} plate={cleaned} valid={is_valid}")

        latency_ms = (time.time() - t0) * 1000
        if frame_count % 10 == 0:
            print(f"frame={frame_count} latency_ms={latency_ms:.1f}")

    cap.release()
    print("Smoke run complete.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="0", help="Camera index or file path")
    parser.add_argument("--frames", type=int, default=60, help="Max frames for smoke run")
    return parser.parse_args()


def normalize_source(source: str) -> str | int:
    if source.isdigit():
        return int(source)
    return source


if __name__ == "__main__":
    args = parse_args()
    run_smoke(video_source=normalize_source(args.source), max_frames=args.frames)
