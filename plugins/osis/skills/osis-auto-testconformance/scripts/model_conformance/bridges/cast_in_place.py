"""现浇连续箱梁 — 简化 5 维;以及桥型未知兜底。"""
from __future__ import annotations

from typing import Any

from ..common import _assemble, _rating_of

_SIMPLE_H_OVER_L = {
    "precast_small_box": (1 / 22, 1 / 16),
    "t_girder": (1 / 18, 1 / 14),
    "cast_in_place_box": (1 / 22, 1 / 15),
    "hollow_slab": (1 / 24, 1 / 16),
}

_SIMPLE_L_RANGE = {
    "precast_small_box": (10.0, 50.0),
    "t_girder": (10.0, 50.0),  # 仅作报告兜底;T 梁 D1 走 RC/PC 分档
    "cast_in_place_box": (15.0, 60.0),
    "hollow_slab": (6.0, 25.0),
}


def _score_simple_d1_span(L: float | None, valid_range: tuple[float, float]) -> tuple[float, dict[str, Any]]:
    """D1 跨径提取:在桥型合理跨径区间内 → 1.0;偏离 → 0.5/0。"""
    lo, hi = valid_range
    if L is None:
        return 0.0, {"issue": "未能从节点/支座提取跨径"}
    if lo <= L <= hi:
        return 1.0, {"actual": L, "valid_range": list(valid_range), "level": "ok"}
    rel = min(abs(L - lo), abs(L - hi)) / hi
    if rel <= 0.2:
        score, level = 0.5, "warn"
    else:
        score, level = 0.0, "fail"
    return score, {"actual": L, "valid_range": list(valid_range), "level": level,
                   "issue": f"跨径 {L} 偏离该桥型典型区间 [{lo}, {hi}] m"}


def _score_simple_d2_height(L: float | None, H: float | None, ratio_band: tuple[float, float]) -> tuple[float, dict[str, Any]]:
    """D2 梁高合理性:H/L 落在经验区间内。

    变截面桥 H_root≠H_mid,简支梁 H 通常单一(取 H_root=最大梁高)。
    """
    if L is None or H is None or L <= 0:
        return 0.0, {"issue": "L 或 H 缺失,无法核对梁高比"}
    lo_r, hi_r = ratio_band
    ratio = H / L
    if lo_r <= ratio <= hi_r:
        score, level = 1.0, "ok"
    elif min(abs(ratio - lo_r), abs(ratio - hi_r)) <= 0.005:
        score, level = 0.5, "warn"
    else:
        score, level = 0.0, "fail"
    issue = None if score >= 0.5 else f"H/L={ratio:.4f} 不在经验区间 [{lo_r:.4f}, {hi_r:.4f}](H={H}, L={L})"
    return score, {"H": H, "L": L, "H_over_L": round(ratio, 4),
                   "expected_band": [round(lo_r, 4), round(hi_r, 4)], "level": level, "issue": issue}


def _score_simple_d3_section(section_count: int, girder_section_count: int, expected_type_kw: str, section_types: list[str]) -> tuple[float, dict[str, Any]]:
    """D3 截面定义:主梁截面数 ≥1,且截面类型命中桥型期望关键字。"""
    issues: list[str] = []
    score = 1.0
    if girder_section_count < 1:
        score -= 0.6
        issues.append(f"主梁截面数 {girder_section_count} < 1")
    type_hit = any(expected_type_kw in t.upper() for t in section_types)
    if not type_hit and section_types:
        score -= 0.4
        issues.append(f"截面类型 {section_types} 未命中期望 {expected_type_kw}")
    return max(0.0, score), {"section_count": section_count, "girder_section_count": girder_section_count,
                              "section_types": section_types, "expected_type": expected_type_kw, "issues": issues}


def _score_simple_d4_stages(stage_count: int, is_continuous: bool) -> tuple[float, dict[str, Any]]:
    """D4 施工阶段:简支 ≥3;简支变连续(体系转换)≥4。is_continuous 由调用方传入。"""
    issues: list[str] = []
    threshold = 4 if is_continuous else 3
    if stage_count >= threshold:
        score = 1.0
    elif stage_count >= threshold - 1:
        score = 0.5
        issues.append(f"阶段数 {stage_count} 偏少(建议 ≥{threshold})")
    else:
        score = 0.0
        issues.append(f"阶段数 {stage_count} 过少(<{threshold})")
    if is_continuous and stage_count < 4:
        issues.append("简支变连续应有体系转换阶段(临时支座拆除/支座转换)")
    return score, {"stage_count": stage_count, "threshold": threshold, "is_continuous": is_continuous, "issues": issues}


def _score_simple_d5_completeness(p: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """D5 结构完整性:节点/单元/边界/工况齐全。"""
    score = 1.0
    issues: list[str] = []
    if p["node_count"] < 5:
        score -= 0.3
        issues.append(f"节点数 {p['node_count']} 过少(<5)")
    if p["element_count"] < 1:
        score -= 0.3
        issues.append("未检测到单元定义(engine.element.create)")
    if p["boundary_count"] < 1:
        score -= 0.2
        issues.append("未检测到边界定义(engine.boundary.create)")
    if p["stage_count"] < 2:
        score -= 0.2
        issues.append(f"阶段数 {p['stage_count']} < 2")
    return max(0.0, score), {"node_count": p["node_count"], "element_count": p["element_count"],
                              "boundary_count": p["boundary_count"], "stage_count": p["stage_count"], "issues": issues}



def score_cast_in_place(params: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    btype = params.get("bridge_type") or "cast_in_place_box"
    L = params.get("L")
    H = params.get("H_root")
    is_continuous = bool(params.get("is_continuous"))
    valid_range = _SIMPLE_L_RANGE.get(btype, (15.0, 60.0))
    ratio_band = _SIMPLE_H_OVER_L.get(btype, (1 / 22, 1 / 15))
    d1, d1d = _score_simple_d1_span(L, valid_range)
    d2, d2d = _score_simple_d2_height(L, H, ratio_band)
    d3, d3d = _score_simple_d3_section(
        params["section_count"], params["girder_section_count"],
        "CONVENTIONALBOX", params["section_types"],
    )
    d4, d4d = _score_simple_d4_stages(params["stage_count"], is_continuous)
    d5, d5d = _score_simple_d5_completeness(params)
    return _assemble(params, [
        ("D1_span", d1, d1d), ("D2_beam_height", d2, d2d), ("D3_section", d3, d3d),
        ("D4_stages", d4, d4d), ("D5_completeness", d5, d5d),
    ])


def score_unknown(params: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """兜底:无法识别桥型 → 只评结构完整性。"""
    d5, d5d = _score_simple_d5_completeness(params)
    return d5 / 5.0, {
        "total_score": round(d5, 3),
        "max_dim": 5,
        "rating": _rating_of(d5, 5),
        "params": params,
        "dimensions": {"D5_completeness": {"score_5": round(d5, 3), **d5d}},
        "note": "桥型未识别,仅做结构完整性兜底评价",
    }
