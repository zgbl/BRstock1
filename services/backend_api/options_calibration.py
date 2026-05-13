import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CALIBRATION_PATH = PROJECT_ROOT / "Data" / "option_synth_calibration.json"
BUNDLED_CALIBRATION_PATH = Path(__file__).resolve().parent / "config_data" / "option_synth_calibration.json"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "Data" / "option_chain_calibration_reports.jsonl"


def calibration_path() -> Path:
    raw = os.getenv("OPTION_SYNTH_CALIBRATION_PATH")
    return Path(raw).expanduser() if raw else DEFAULT_CALIBRATION_PATH


def bundled_calibration_path() -> Path:
    raw = os.getenv("OPTION_SYNTH_BUNDLED_CALIBRATION_PATH")
    return Path(raw).expanduser() if raw else BUNDLED_CALIBRATION_PATH


def reports_path() -> Path:
    raw = os.getenv("OPTION_CHAIN_CALIBRATION_REPORT_PATH")
    return Path(raw).expanduser() if raw else DEFAULT_REPORT_PATH


def empty_calibration() -> Dict[str, Any]:
    return {"version": 0, "updated_at": None, "buckets": {}}


def _read_calibration(target: Path) -> Optional[Dict[str, Any]]:
    try:
        if target.exists():
            model = json.loads(target.read_text())
            if isinstance(model, dict):
                model.setdefault("buckets", {})
                return model
    except Exception:
        pass
    return None


def calibration_candidates(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    if path is not None:
        return [{"kind": "runtime", "path": Path(path)}]
    return [
        {"kind": "runtime", "path": calibration_path()},
        {"kind": "bundled", "path": bundled_calibration_path()},
    ]


def load_calibration_with_source(path: Optional[Path] = None) -> Dict[str, Any]:
    for candidate in calibration_candidates(path):
        model = _read_calibration(candidate["path"])
        if model is not None:
            return {
                "model": model,
                "source_kind": candidate["kind"],
                "source_path": str(candidate["path"]),
            }
    return {
        "model": empty_calibration(),
        "source_kind": "empty",
        "source_path": None,
    }


def load_calibration(path: Optional[Path] = None) -> Dict[str, Any]:
    return load_calibration_with_source(path)["model"]


def save_calibration(model: Dict[str, Any], path: Optional[Path] = None) -> None:
    target = path or calibration_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(model, indent=2, sort_keys=True))


def append_report(report: Dict[str, Any], path: Optional[Path] = None) -> None:
    target = path or reports_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a") as handle:
        handle.write(json.dumps(report, sort_keys=True) + "\n")


def dte_bucket(dte: Any) -> str:
    value = int(float(dte or 0))
    if value <= 14:
        return "DTE_00_14"
    if value <= 30:
        return "DTE_15_30"
    if value <= 60:
        return "DTE_31_60"
    if value <= 120:
        return "DTE_61_120"
    return "DTE_121_PLUS"


def delta_bucket(delta: Any) -> str:
    value = abs(float(delta or 0))
    if value < 0.15:
        return "DELTA_00_15"
    if value < 0.30:
        return "DELTA_15_30"
    if value < 0.45:
        return "DELTA_30_45"
    if value < 0.60:
        return "DELTA_45_60"
    if value < 0.75:
        return "DELTA_60_75"
    return "DELTA_75_100"


def bucket_key(symbol: str, option_type: str, dte: Any, delta: Any) -> str:
    return "|".join([
        str(symbol or "").upper(),
        str(option_type or "").upper(),
        dte_bucket(dte),
        delta_bucket(delta),
    ])


def safe_float(value: Any) -> Optional[float]:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except Exception:
        return None


def pct_error(model_value: float, real_value: float) -> Optional[float]:
    if not real_value:
        return None
    return (model_value - real_value) / real_value


def summarize_errors(rows: Iterable[Dict[str, Any]], prefix: str = "error_pct") -> Dict[str, Any]:
    values = sorted(abs(float(row[prefix])) for row in rows if row.get(prefix) is not None and math.isfinite(float(row[prefix])))
    if not values:
        return {"sample_count": 0}
    p90_index = min(max(int(math.ceil(len(values) * 0.90)) - 1, 0), len(values) - 1)
    return {
        "sample_count": len(values),
        "median_abs_error_pct": round(median(values) * 100, 2),
        "p90_abs_error_pct": round(values[p90_index] * 100, 2),
        "mean_abs_error_pct": round((sum(values) / len(values)) * 100, 2),
    }


def build_bucket_updates(rows: List[Dict[str, Any]], min_samples: int = 3) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["bucket_key"], []).append(row)

    updates: Dict[str, Dict[str, Any]] = {}
    for key, bucket_rows in grouped.items():
        if len(bucket_rows) < min_samples:
            continue
        mid_ratios = [
            row["real_mid"] / row["synth_mid"]
            for row in bucket_rows
            if row.get("real_mid") and row.get("synth_mid") and row["synth_mid"] > 0
        ]
        spread_ratios = [
            row["real_spread"] / row["synth_spread"]
            for row in bucket_rows
            if row.get("real_spread") is not None and row.get("synth_spread") and row["synth_spread"] > 0
        ]
        iv_shifts = [
            row["real_iv"] - row["synth_iv"]
            for row in bucket_rows
            if row.get("real_iv") is not None and row.get("synth_iv") is not None
        ]
        delta_biases = [
            row["real_delta"] - row["synth_delta"]
            for row in bucket_rows
            if row.get("real_delta") is not None and row.get("synth_delta") is not None
        ]
        if not mid_ratios:
            continue
        updates[key] = {
            "sample_count": len(bucket_rows),
            "mid_multiplier": round(min(max(median(mid_ratios), 0.50), 1.80), 6),
            "spread_multiplier": round(min(max(median(spread_ratios), 0.50), 3.00), 6) if spread_ratios else 1.0,
            "iv_shift": round(min(max(median(iv_shifts), -0.20), 0.20), 6) if iv_shifts else 0.0,
            "delta_bias": round(min(max(median(delta_biases), -0.20), 0.20), 6) if delta_biases else 0.0,
            "before": summarize_errors(bucket_rows),
        }
    return updates


def merge_calibration_updates(
    existing: Dict[str, Any],
    updates: Dict[str, Dict[str, Any]],
    blend: float = 0.35,
) -> Dict[str, Any]:
    model = dict(existing or {})
    buckets = dict(model.get("buckets") or {})
    blend = min(max(float(blend), 0.0), 1.0)
    now = datetime.now(timezone.utc).isoformat()

    for key, update in updates.items():
        previous = buckets.get(key) or {}
        if previous:
            merged = {
                "mid_multiplier": round((previous.get("mid_multiplier", 1.0) * (1 - blend)) + (update["mid_multiplier"] * blend), 6),
                "spread_multiplier": round((previous.get("spread_multiplier", 1.0) * (1 - blend)) + (update["spread_multiplier"] * blend), 6),
                "iv_shift": round((previous.get("iv_shift", 0.0) * (1 - blend)) + (update["iv_shift"] * blend), 6),
                "delta_bias": round((previous.get("delta_bias", 0.0) * (1 - blend)) + (update["delta_bias"] * blend), 6),
                "sample_count": int(previous.get("sample_count", 0)) + int(update.get("sample_count", 0)),
            }
        else:
            merged = dict(update)
        merged["updated_at"] = now
        merged["last_batch_sample_count"] = int(update.get("sample_count", 0))
        merged["before"] = update.get("before")
        buckets[key] = merged

    model["buckets"] = buckets
    model["version"] = int(model.get("version") or 0) + 1
    model["updated_at"] = now
    return model
