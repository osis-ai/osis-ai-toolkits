"""简支空心板 — 经济性 5 维(D1–D3 + D4 空心率 + D5 建设期)。"""
from __future__ import annotations

from typing import Any

from ..common import _assemble
from ._helpers import is_pc, level_of, pack

# D2 跨径-梁高锚点:(跨径 m, L/H 下限, L/H 上限)
_LH_ANCHORS: list[tuple[float, float, float]] = [
    (6, 10.9, 15),
    (8, 12.3, 16),
    (10, 13.3, 16.7),
    (13, 15.2, 18.6),
    (16, 16.8, 20),
    (20, 19, 22.3),
    (25, 20, 24),
]


def _get_lh_bounds(L: float) -> tuple[float, float, float]:
    """返回 (lh_low, lh_high, thin_ded)。thick_ded 恒为 0.5。"""
    if L < 6:
        return 10.9, 15, 0.2
    if L > 25:
        return 20, 24, 0.2
    for i in range(len(_LH_ANCHORS) - 1):
        L1, low1, high1 = _LH_ANCHORS[i]
        L2, low2, high2 = _LH_ANCHORS[i + 1]
        if L1 <= L <= L2:
            t = (L - L1) / (L2 - L1)
            return low1 + (low2 - low1) * t, high1 + (high2 - high1) * t, 0.25
    return 20, 24, 0.25


def _score_hollow_slab_d1_span(L: float | None, is_prestressed: bool) -> tuple[float, dict[str, Any]]:
    if L is None:
        return 0.0, {"issue": "未能从节点/支座提取跨径 L", "level": "fail", "girder_system": None}
    system = "PC" if is_prestressed else "RC"
    if is_prestressed:
        if 10.0 <= L <= 20.0:
            deduction, band = 0.0, "10~20m(合理)"
        elif 20.0 < L <= 22.0:
            deduction, band = 0.15, "20~22m"
        elif 8.0 <= L < 10.0 or 22.0 < L <= 25.0:
            deduction, band = 0.3, "8~10m 或 22~25m"
        else:
            deduction, band = 1.0, "<8m 或 >25m"
        valid = [10.0, 20.0]
    else:
        if 6.0 <= L <= 13.0:
            deduction, band = 0.0, "6~13m(合理)"
        elif 4.0 <= L < 6.0 or 13.0 < L <= 16.0:
            deduction, band = 0.5, "4~6m 或 13~16m"
        else:
            deduction, band = 1.0, "<4m 或 >16m"
        valid = [6.0, 13.0]
    score = max(0.0, 1.0 - deduction)
    issue = None if score >= 1.0 - 1e-9 else f"{system}空心板跨径 L={L:.1f} m 落在{band},扣 {deduction:.2f}"
    return score, {
        "actual": L, "girder_system": system, "valid_range": valid, "band": band,
        "deduction": deduction, "level": level_of(score), "issue": issue,
    }


def _score_hollow_slab_d2_height(
    L: float | None, H: float | None,
) -> tuple[float, dict[str, Any]]:
    if L is None or H is None or L <= 0:
        return 0.0, {"issue": "L 或 H 缺失", "level": "fail"}
    lh = L / H
    lh_low, lh_high, thin_ded = _get_lh_bounds(L)

    if lh_low <= lh <= lh_high:
        deduction, band = 0.0, f"L/H={lh_low:.1f}~{lh_high:.1f}(合理)"
    elif lh_high < lh <= lh_high + 1:
        deduction, band = thin_ded, f"L/H={lh_high:.1f}~{lh_high + 1:.1f}(偏细高)"
    elif lh_low - 1 <= lh < lh_low:
        deduction, band = 0.5, f"L/H={lh_low - 1:.1f}~{lh_low:.1f}(偏粗矮)"
    else:
        deduction, band = 1.0, "L/H 超出合理范围±1"

    score = max(0.0, 1.0 - deduction)
    h_over_l = round(H / L, 4)
    issue = None if score >= 1.0 - 1e-9 else (
        f"空心板 H/L={h_over_l}(H={H}, L={L}, L/H={lh:.2f}) 落在{band},扣 {deduction:.2f}"
    )
    return score, {
        "H": H, "L": L, "H_over_L": h_over_l, "L_over_H": round(lh, 2),
        "expected_lh": [round(lh_low, 1), round(lh_high, 1)],
        "band": band, "deduction": deduction,
        "level": level_of(score), "issue": issue,
    }


def _score_hollow_slab_d3_section(
    mid: dict[str, Any] | None,
    support: dict[str, Any] | None,
) -> tuple[float, dict[str, Any]]:
    """D3 截面常规尺寸:4 小项各 25%,每项 0/1。"""
    issues: list[str] = []
    sub: dict[str, float] = {}

    if not mid:
        return 0.0, {"level": "fail", "issues": ["未能提取 HOLLOWSLAB 跨中截面"], "sub_scores": {}}

    tt, tb, tw, bc = mid.get("tt"), mid.get("tb"), mid.get("tw"), mid.get("bc")

    # 1. 顶底板 25%
    plates = [v for v in (tt, tb) if v is not None]
    if not plates:
        sub["plate"] = 0.0
        issues.append("顶底板厚度缺失")
    elif min(plates) < 0.08 or max(plates) > 0.15:
        sub["plate"] = 0.0
        issues.append(f"顶底板厚 tt={tt}, tb={tb} 超出 0.08~0.15 m")
    else:
        sub["plate"] = 1.0

    # 2. 腹板 Tw 25%
    if tw is None:
        sub["web"] = 0.0
        issues.append("腹板厚 tw 缺失")
    elif tw < 0.1 or tw > 0.2:
        sub["web"] = 0.0
        issues.append(f"腹板厚 tw={tw:.3f} m 超出 0.1~0.2")
    else:
        sub["web"] = 1.0

    # 3. 边梁 Bc 25%
    if bc is None:
        sub["cantilever"] = 0.0
        issues.append("边梁 Bc 缺失")
    elif bc < 0.35 or bc > 0.85:
        sub["cantilever"] = 0.0
        issues.append(f"边梁 Bc={bc:.3f} m 超出 0.35~0.85")
    else:
        sub["cantilever"] = 1.0

    # 4. 支点加厚段 ≥ 跨中 25%(仅查 tt/tb/tw)
    if support:
        smaller = [k for k in ("tt", "tb", "tw")
                   if mid.get(k) is not None and support.get(k) is not None and support[k] < mid[k]]
        if smaller:
            sub["support"] = 0.0
            issues.append("支点加厚段尺寸小于跨中(" + "; ".join(smaller) + ")")
        else:
            sub["support"] = 1.0
    else:
        sub["support"] = 1.0  # 无支点截面不扣

    score = sum(sub.values()) / 4.0
    return score, {
        "mid_name": mid.get("name"), "tt": tt, "tb": tb, "tw": tw, "bc": bc,
        "support_name": support.get("name") if support else None,
        "sub_scores": sub,
        "level": level_of(score), "issues": issues,
    }


def _score_hollow_slab_d4_void(void_ratio: float | None) -> tuple[float, dict[str, Any]]:
    """空心板 D4 截面经济性:空心率。"""
    issues: list[str] = []
    deduction = 0.0

    if void_ratio is None:
        deduction = 0.5
        issues.append("未能估算空心率,扣 0.5")
    elif 0.45 <= void_ratio <= 0.52:
        pass
    elif 0.40 <= void_ratio < 0.45 or 0.52 < void_ratio <= 0.55:
        deduction = 0.15
        issues.append(f"空心率 {void_ratio:.3f} 落在边缘带,扣 0.15")
    elif 0.36 <= void_ratio < 0.40 or 0.55 < void_ratio <= 0.59:
        deduction = 0.5
        issues.append(f"空心率 {void_ratio:.3f} 偏离较大,扣 0.5")
    else:
        deduction = 1.0
        issues.append(f"空心率 {void_ratio:.3f} 严重偏离,扣 1.0")

    score = max(0.0, 1.0 - deduction)
    return pack(score, {
        "void_ratio": None if void_ratio is None else round(void_ratio, 4),
    }, issues, deduction)


def _score_hollow_slab_d5_economy(
    concrete_ratio: float | None,
    pst_steel_ratio: float | None,
    beam_width: float | None,
    stage_count: int,
    stage_names: list[str] | None,
) -> tuple[float, dict[str, Any]]:
    """D5 建设期经济性:4 小项加权(混凝土30% + 钢绞线30% + 板宽20% + 阶段20%)。"""
    issues: list[str] = []
    sub: dict[str, float] = {}

    # 1. 混凝土折算厚度 30%
    if concrete_ratio is None:
        sub["concrete"] = 0.0
        issues.append("未能提取混凝土折算厚度")
    elif 0.25 <= concrete_ratio <= 0.55:
        sub["concrete"] = 1.0
    elif 0.55 < concrete_ratio <= 0.65:
        ded = 3.0 * (concrete_ratio - 0.55)  # linear 0→0.3
        sub["concrete"] = 1.0 - ded
        issues.append(f"混凝土折算厚度 {concrete_ratio:.4f} 偏大(0.55~0.65),扣 {ded:.2f}")
    else:
        sub["concrete"] = 0.0
        issues.append(f"混凝土折算厚度 {concrete_ratio:.4f} 超出 0.25~0.65")

    # 2. 预应力钢绞线用量 30%
    if pst_steel_ratio is None:
        sub["steel"] = 0.0
        issues.append("未能提取预应力钢绞线用量")
    elif 25 <= pst_steel_ratio <= 49:
        sub["steel"] = 1.0
    elif 18 <= pst_steel_ratio < 25:
        ded = 0.2 * (25 - pst_steel_ratio) / 7.0  # linear 0→0.2
        sub["steel"] = 1.0 - ded
        issues.append(f"钢绞线用量 {pst_steel_ratio:.1f} kg/m³ 偏低(18~25),扣 {ded:.2f}")
    else:
        sub["steel"] = 0.0
        issues.append(f"钢绞线用量 {pst_steel_ratio:.1f} kg/m³ 超出 18~49")

    # 3. 板宽 20%
    if beam_width is None:
        sub["width"] = 0.0
        issues.append("未能提取板宽")
    elif 1.0 <= beam_width <= 1.8:
        sub["width"] = 1.0
    else:
        sub["width"] = 0.0
        issues.append(f"板宽 {beam_width:.3f} m 超出 1.0~1.8")

    # 4. 施工阶段 20%
    names = list(stage_names or [])
    blob = "".join(names)
    missing = [k for k in ("预制", "存梁", "二期", "徐变") if k not in blob]
    if stage_count >= 4 and not missing:
        sub["stage"] = 1.0
    else:
        sub["stage"] = 0.0
        if stage_count < 4:
            issues.append(f"施工阶段数 {stage_count} < 4")
        if missing:
            issues.append("施工阶段缺少「" + "、".join(missing) + "」")

    score = sub["concrete"] * 0.3 + sub["steel"] * 0.3 + sub["width"] * 0.2 + sub["stage"] * 0.2
    return score, {
        "concrete_ratio": None if concrete_ratio is None else round(concrete_ratio, 4),
        "pst_steel_ratio": None if pst_steel_ratio is None else round(pst_steel_ratio, 1),
        "beam_width": None if beam_width is None else round(beam_width, 4),
        "stage_count": stage_count, "stage_names": names,
        "sub_scores": sub,
        "level": level_of(score), "issues": issues,
    }



def score_hollow_slab(params: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    pc = is_pc(params)
    L, H = params.get("L"), params.get("H_root")
    dims = [
        ("D1_span", *_score_hollow_slab_d1_span(L, pc)),
        ("D2_beam_height", *_score_hollow_slab_d2_height(L, H)),
        ("D3_section", *_score_hollow_slab_d3_section(
            params.get("hollow_slab_mid"), params.get("hollow_slab_support"),
        )),
        ("D4_void_ratio", *_score_hollow_slab_d4_void(params.get("void_ratio"))),
        ("D5_economy", *_score_hollow_slab_d5_economy(
            params.get("concrete_ratio"), params.get("pst_steel_ratio"),
            params.get("beam_width"),
            int(params.get("stage_count") or 0), params.get("stage_names") or [],
        )),
    ]
    weights = {"D1_span": 0.25, "D2_beam_height": 0.25, "D3_section": 0.20,
               "D4_void_ratio": 0.10, "D5_economy": 0.20}
    return _assemble(params, dims, weights=weights)
