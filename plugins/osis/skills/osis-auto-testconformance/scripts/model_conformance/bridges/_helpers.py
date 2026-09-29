"""预制梁评分共用小工具(扣分打包 / 阶段关键字 / 支点≥跨中)。"""
from __future__ import annotations

from typing import Any

STAGE_KEYS = ("预制", "存梁", "二期", "徐变")


def level_of(score: float) -> str:
    if score >= 1.0 - 1e-9:
        return "ok"
    if score > 0.0:
        return "warn"
    return "fail"


def pack(
    score: float,
    measures: dict[str, Any],
    issues: list[str],
    deduction: float,
) -> tuple[float, dict[str, Any]]:
    return score, {
        **measures,
        "deduction": round(deduction, 3),
        "level": level_of(score),
        "issues": issues,
        "issue": issues[0] if issues else None,
    }


def support_not_smaller(
    mid: dict[str, Any],
    support: dict[str, Any] | None,
    keys: tuple[str, ...],
) -> list[str]:
    if not support:
        return []
    smaller: list[str] = []
    for k in keys:
        mv, sv = mid.get(k), support.get(k)
        if mv is None or sv is None:
            continue
        if sv + 1e-9 < mv:
            smaller.append(f"{k}:支点{sv}<跨中{mv}")
    return smaller


def stage_deduct(
    stage_count: int,
    stage_names: list[str] | None,
) -> tuple[float, list[str], bool]:
    names = list(stage_names or [])
    blob = "".join(names)
    missing = [k for k in STAGE_KEYS if k not in blob]
    ok = stage_count >= 4 and not missing
    if ok:
        return 0.0, [], True
    issues: list[str] = []
    if stage_count < 4:
        issues.append(f"施工阶段数 {stage_count} < 4,扣 0.25")
    elif missing:
        issues.append("施工阶段缺少「" + "、".join(missing) + "」,扣 0.25")
    return 0.25, issues, False


def is_pc(params: dict[str, Any]) -> bool:
    if params.get("is_prestressed") is not None:
        return bool(params["is_prestressed"])
    return bool(params.get("has_prestress"))


def thickness_band(
    val: float | None,
    name: str,
    full: tuple[float, float],
    soft_lo: tuple[float, float],
    soft_hi: tuple[float, float],
) -> tuple[float, str | None]:
    if val is None:
        return 1.0, f"{name} 缺失,扣 1.0"
    lo, hi = full
    if lo <= val <= hi:
        return 0.0, None
    slo0, slo1 = soft_lo
    shi0, shi1 = soft_hi
    if slo0 <= val < slo1 or shi0 < val <= shi1:
        return 0.25, f"{name}={val:.3f} m 落在边缘带,扣 0.25"
    return 1.0, f"{name}={val:.3f} m 超出合理范围,扣 1.0"
