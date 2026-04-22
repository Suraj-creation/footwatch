from __future__ import annotations

import re

_PLATE_PATTERN = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$")
_BH_PATTERN = re.compile(r"^[0-9]{2}BH[0-9]{4}[A-Z]{2}$")


def normalize_plate(raw: str | None) -> str:
    if raw is None:
        return ""

    text = str(raw).upper().strip().replace(" ", "").replace("-", "")
    return re.sub(r"[^A-Z0-9]", "", text)


def is_valid_plate(value: str | None) -> bool:
    plate = normalize_plate(value)
    if not plate:
        return False

    return bool(_PLATE_PATTERN.match(plate) or _BH_PATTERN.match(plate))
