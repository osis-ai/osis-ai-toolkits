"""简支 / 简支变连续小箱梁 — 经济性 5 维(D1–D5)。"""
from __future__ import annotations

from typing import Any

from ..common import _assemble
from ._helpers import level_of, thickness_band

def _score_small_box_d1_span(L: float | None) -> tuple[float, dict[str, Any]]:
    """PC 简支小箱梁 D1:20~40 满分;16~20 / 40~45 线性扣 0~0.5;外侧扣 1。"""
    if L is None:
        return 0.0, {"issue": "未能从节点/支座提取跨径 L", "level": "fail", "deduction": 1.0}
    if 20.0 <= L <= 40.0:
        deduction, band = 0.0, "20~40m(合理)"
    elif 40.0 < L <= 45.0:
        deduction = 0.5 * (L - 40.0) / 5.0
        band = "40~45m(偏大,线性扣分)"
    elif 16.0 <= L < 20.0:
        deduction = 0.5 * (20.0 - L) / 4.0
        band = "16~20m(偏小,线性扣分)"
    else:
        deduction, band = 1.0, "<16m 或 >45m(不适配)"
    score = max(0.0, 1.0 - deduction)
    issue = None if score >= 1.0 - 1e-9 else f"小箱梁跨径 L={L:.1f} m 落在{band},扣 {deduction:.2f}"
    return score, {
        "actual": L, "valid_range": [20.0, 40.0], "band": band,
        "deduction": round(deduction, 3), "level": level_of(score), "issue": issue,
    }


# D2 跨径-梁高锚点:(跨径 m, L/H 下限, L/H 上限)
_LH_ANCHORS: list[tuple[float, float, float]] = [
    (16, 14.5, 18.9),
    (20, 15.3, 18.2),
    (25, 16.6, 19.3),
    (30, 16.6, 19.0),
    (35, 17.5, 19.5),
    (40, 17.3, 19.1),
]


def _get_lh_bounds(L: float) -> tuple[float, float, float, float | None]:
    """返回 (lh_low, lh_high, thin_ded, thick_ded)。thick_ded=None 表示无厚侧缓冲。"""
    if L < 16:
        return 14.5, 18.9, 0.25, None
    if L > 40:
        return 17.3, 19.1, 0.25, 0.5
    for i in range(len(_LH_ANCHORS) - 1):
        L1, low1, high1 = _LH_ANCHORS[i]
        L2, low2, high2 = _LH_ANCHORS[i + 1]
        if L1 <= L <= L2:
            t = (L - L1) / (L2 - L1)
            return low1 + (low2 - low1) * t, high1 + (high2 - high1) * t, 0.25, 0.5
    return 17.3, 19.1, 0.25, 0.5


def _score_small_box_d2_height(L: float | None, H: float | None) -> tuple[float, dict[str, Any]]:
    if L is None or H is None or L <= 0:
        return 0.0, {"issue": "L 或 H 缺失", "level": "fail"}
    lh = L / H
    lh_low, lh_high, thin_ded, thick_ded = _get_lh_bounds(L)

    if lh_low <= lh <= lh_high:
        deduction, band = 0.0, f"L/H={lh_low:.1f}~{lh_high:.1f}(合理)"
    elif lh_high < lh <= lh_high + 1:
        deduction, band = thin_ded, f"L/H={lh_high:.1f}~{lh_high + 1:.1f}(偏细高)"
    elif thick_ded is not None and lh_low - 1 <= lh < lh_low:
        deduction, band = thick_ded, f"L/H={lh_low - 1:.1f}~{lh_low:.1f}(偏粗矮)"
    else:
        deduction, band = 1.0, "L/H 超出合理范围"

    score = max(0.0, 1.0 - deduction)
    h_over_l = round(H / L, 4)
    issue = None if score >= 1.0 - 1e-9 else (
        f"小箱梁 H/L={h_over_l}(H={H}, L={L}, L/H={lh:.2f}) 落在{band},扣 {deduction:.2f}"
    )
    return score, {
        "H": H, "L": L, "H_over_L": h_over_l, "L_over_H": round(lh, 2),
        "expected_lh": [round(lh_low, 1), round(lh_high, 1)],
        "band": band, "deduction": deduction, "level": level_of(score), "issue": issue,
    }


def _score_small_box_d3_section(
    mid: dict[str, Any] | None,
    support: dict[str, Any] | None,
) -> tuple[float, dict[str, Any]]:
    """D3 截面常规尺寸:5 小项各 20%。"""
    issues: list[str] = []
    sub: dict[str, float] = {}

    if not mid:
        return 0.0, {"level": "fail", "issues": ["未能提取 SMALLBOX 跨中截面"], "sub_scores": {}}

    # 1. 顶板 tt 20%
    d_tt, msg_tt = thickness_band(mid.get("tt"), "顶板厚 tt", (0.16, 0.22), (0.15, 0.16), (0.22, 0.25))
    sub["tt"] = 1.0 - d_tt
    if msg_tt:
        issues.append(msg_tt)

    # 2. 底板 tb 20%
    d_tb, msg_tb = thickness_band(mid.get("tb"), "底板厚 tb", (0.16, 0.22), (0.14, 0.16), (0.22, 0.25))
    sub["tb"] = 1.0 - d_tb
    if msg_tb:
        issues.append(msg_tb)

    # 3. 腹板 tw 20%
    d_tw, msg_tw = thickness_band(mid.get("tw"), "腹板厚 tw", (0.16, 0.22), (0.14, 0.16), (0.22, 0.25))
    sub["tw"] = 1.0 - d_tw
    if msg_tw:
        issues.append(msg_tw)

    # 4. 腋角 20%(上梗腋 + 下梗腋各占一半)
    haunch = 1.0
    xi1 = mid.get("xi1")
    if xi1 is None or xi1 < 0.12:
        haunch -= 0.5
        issues.append(f"上梗腋宽 xi1={xi1} < 0.12 m")
    xi2 = mid.get("xi2")
    if xi2 is None or xi2 < 0.04:
        haunch -= 0.5
        issues.append(f"下梗腋宽 xi2={xi2} < 0.04 m")
    sub["haunch"] = max(0.0, haunch)

    # 5. 支点加厚段 ≥ 跨中 20%(仅查 tt/tb/tw)
    if support:
        smaller = [k for k in ("tt", "tb", "tw")
                   if mid.get(k) is not None and support.get(k) is not None and support[k] < mid[k]]
        if smaller:
            sub["support"] = 0.0
            issues.append("支点加厚段尺寸小于跨中(" + "; ".join(smaller) + ")")
        else:
            sub["support"] = 1.0
    else:
        sub["support"] = 1.0

    score = sum(sub.values()) / 5.0
    return score, {
        "mid_name": mid.get("name"), "tt": mid.get("tt"), "tb": mid.get("tb"),
        "tw": mid.get("tw"), "xi1": xi1, "xi2": xi2,
        "support_name": support.get("name") if support else None,
        "sub_scores": sub,
        "level": level_of(score), "issues": issues,
    }


def _score_small_box_d4_economy(
    concrete_ratio: float | None,
    pst_steel_ratio: float | None,
) -> tuple[float, dict[str, Any]]:
    """D4 建设期经济性:混凝土折算厚度 50% + 钢绞线用量 50%。"""
    issues: list[str] = []
    sub: dict[str, float] = {}

    # 1. 混凝土折算厚度 50%
    if concrete_ratio is None:
        sub["concrete"] = 0.0
        issues.append("未能提取混凝土折算厚度")
    elif 0.37 <= concrete_ratio <= 0.65:
        sub["concrete"] = 1.0
    elif 0.65 < concrete_ratio <= 0.75:
        ded = 5.0 * (concrete_ratio - 0.65)  # linear 0→0.5
        sub["concrete"] = 1.0 - ded
        issues.append(f"混凝土折算厚度 {concrete_ratio:.4f} 偏大(0.65~0.75),扣 {ded:.2f}")
    else:
        sub["concrete"] = 0.0
        issues.append(f"混凝土折算厚度 {concrete_ratio:.4f} 超出 0.37~0.75")

    # 2. 预应力钢绞线用量 50%
    if pst_steel_ratio is None:
        sub["steel"] = 0.0
        issues.append("未能提取预应力钢绞线用量")
    elif 25 <= pst_steel_ratio <= 46:
        sub["steel"] = 1.0
    elif 18 <= pst_steel_ratio < 25:
        ded = 0.3 * (25 - pst_steel_ratio) / 7.0  # linear 0→0.3
        sub["steel"] = 1.0 - ded
        issues.append(f"钢绞线用量 {pst_steel_ratio:.1f} kg/m³ 偏低(18~25),扣 {ded:.2f}")
    elif 46 < pst_steel_ratio <= 56:
        ded = 0.3 * (pst_steel_ratio - 46) / 10.0  # linear 0→0.3
        sub["steel"] = 1.0 - ded
        issues.append(f"钢绞线用量 {pst_steel_ratio:.1f} kg/m³ 偏高(46~56),扣 {ded:.2f}")
    elif 56 < pst_steel_ratio <= 66:
        ded = 0.3 + 0.7 * (pst_steel_ratio - 56) / 10.0  # linear 0.3→1
        sub["steel"] = 1.0 - ded
        issues.append(f"钢绞线用量 {pst_steel_ratio:.1f} kg/m³ 偏高(56~66),扣 {ded:.2f}")
    else:
        sub["steel"] = 0.0
        issues.append(f"钢绞线用量 {pst_steel_ratio:.1f} kg/m³ 超出 18~66")

    score = sub["concrete"] * 0.5 + sub["steel"] * 0.5
    return score, {
        "concrete_ratio": None if concrete_ratio is None else round(concrete_ratio, 4),
        "pst_steel_ratio": None if pst_steel_ratio is None else round(pst_steel_ratio, 1),
        "sub_scores": sub,
        "level": level_of(score), "issues": issues,
    }



def _score_small_box_d5_standardization(
    beam_width: float | None,
    stage_count: int,
    stage_names: list[str] | None,
) -> tuple[float, dict[str, Any]]:
    """D5 标准化指标:梁宽 50% + 施工阶段 50%。"""
    issues: list[str] = []
    sub: dict[str, float] = {}

    # 1. 梁宽 50%
    if beam_width is None:
        sub["width"] = 0.0
        issues.append("未能提取梁宽")
    elif 2.0 <= beam_width <= 3.2:
        sub["width"] = 1.0
    else:
        sub["width"] = 0.0
        issues.append(f"梁宽 {beam_width:.3f} m 超出 2.0~3.2")

    # 2. 施工阶段 50%
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

    score = sub["width"] * 0.5 + sub["stage"] * 0.5
    return score, {
        "beam_width": None if beam_width is None else round(beam_width, 4),
        "stage_count": stage_count, "stage_names": names,
        "sub_scores": sub,
        "level": level_of(score), "issues": issues,
    }



def score_small_box(params: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    L, H = params.get("L"), params.get("H_root")
    dims = [
        ("D1_span", *_score_small_box_d1_span(L)),
        ("D2_beam_height", *_score_small_box_d2_height(L, H)),
        ("D3_section", *_score_small_box_d3_section(
            params.get("small_box_mid"), params.get("small_box_support"),
        )),
        ("D4_economy", *_score_small_box_d4_economy(
            params.get("concrete_ratio"), params.get("pst_steel_ratio"),
        )),
        ("D5_standardization", *_score_small_box_d5_standardization(
            params.get("beam_width"),
            int(params.get("stage_count") or 0), params.get("stage_names") or [],
        )),
    ]
    weights = {"D1_span": 0.25, "D2_beam_height": 0.25, "D3_section": 0.20,
               "D4_economy": 0.20, "D5_standardization": 0.10}
    return _assemble(params, dims, weights=weights)
