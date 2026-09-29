"""简支 / 简支变连续 T 梁 — 经济性 4 维(D1–D4)。

按跨中标准段马蹄是否外扩分辨:
  - 标准 T / 大 T: bh > tw + 0.02(有马蹄) → 《简支T梁》标准
  - 矮 T: bh ≤ tw + 0.02(无外伸马蹄) → 《简支矮T梁》标准
"""
from __future__ import annotations

from typing import Any, Literal

from ..common import _assemble, _lerp, _pst_steel_ratio_kg_m3, _tgirder_section_area
from ._helpers import is_pc, level_of, support_not_smaller

TVariant = Literal["standard", "low"]

_HOOF_EPS = 0.02  # m: bh 相对 tw 的外扩容差


def _detect_t_variant(mid: dict[str, Any] | None) -> TVariant:
    """无外伸马蹄 → 矮 T,否则标准 T。"""
    if not mid:
        return "standard"
    tw, bh = mid.get("tw"), mid.get("bh")
    if tw is None or bh is None:
        return "standard"
    if float(bh) <= float(tw) + _HOOF_EPS + 1e-9:
        return "low"
    return "standard"


def _variant_label(variant: TVariant) -> str:
    return "矮T梁" if variant == "low" else "T梁"


# ---------------------------------------------------------------------------
# D1 跨径
# ---------------------------------------------------------------------------

def _score_t_girder_d1_span(
    L: float | None,
    is_prestressed: bool,
    variant: TVariant = "standard",
) -> tuple[float, dict[str, Any]]:
    """D1 跨径适配性(大 T 25%)。

    RC: [10,20] 不扣;[8,10) 或 (20,22] 扣 0.6;<8 或 >22 扣 1。
    PC: [20,40] 不扣;(40,50] 扣 0.15;[18,20) 扣 0.3;<18 或 >50 扣 1。
    """
    label = _variant_label(variant)
    if L is None:
        return 0.0, {
            "issue": "未能从节点/支座提取跨径 L,无法评价跨径适配性",
            "girder_system": None,
            "t_variant": variant,
            "level": "fail",
        }

    system = "PC" if is_prestressed else "RC"
    deduction = 0.0
    band = ""

    if variant == "low":
        # 矮 T:通常 PC 密肋;规则不按 RC/PC 分,按跨径表
        valid_range = [10.0, 25.0]
        if 10.0 <= L <= 25.0:
            deduction, band = 0.0, "10~25m(合理)"
        elif 8.0 <= L < 10.0:
            deduction, band = 0.25, "[8,10)m"
        elif 25.0 < L <= 30.0:
            deduction, band = 0.5, "(25,30]m"
        else:
            deduction, band = 1.0, "<8m 或 >30m(不适配)"
        system = "PC"  # 矮 T 文档按预应力装配式
    elif is_prestressed:
        valid_range = [20.0, 40.0]
        if 20.0 <= L <= 40.0:
            deduction, band = 0.0, "20~40m(主流合理)"
        elif 40.0 < L <= 50.0:
            deduction, band = 0.15, "40~50m(可用但偏大)"
        elif 18.0 <= L < 20.0:
            deduction, band = 0.3, "18~20m(偏小)"
        else:
            deduction, band = 1.0, "<18m 或 >50m(不适配)"
    else:
        valid_range = [10.0, 20.0]
        if 10.0 <= L <= 20.0:
            deduction, band = 0.0, "10~20m(合理)"
        elif 8.0 <= L < 10.0 or 20.0 < L <= 22.0:
            deduction, band = 0.6, "8~10m 或 20~22m(边缘)"
        else:
            deduction, band = 1.0, "<8m 或 >22m(不适配)"

    score = max(0.0, 1.0 - deduction)
    issue = None
    if score < 1.0 - 1e-9:
        issue = f"{system}简支{label}跨径 L={L:.1f} m 落在{band},扣 {deduction:.2f}"

    return score, {
        "actual": L,
        "girder_system": system,
        "t_variant": variant,
        "valid_range": valid_range,
        "band": band,
        "deduction": deduction,
        "level": level_of(score),
        "issue": issue,
    }


# D2 PC 大 T 标准跨径表:(L m, L/H 下限=允许最粗矮, L/H 上限=允许最细高)
# 高跨比 1/上限 ~ 1/下限,例如 25m → 1/16.7~1/14.7;20m → 1/16.7~1/13.3。
_PC_LH_ANCHORS: list[tuple[float, float, float]] = [
    (20, 13.3, 16.7),
    (25, 14.7, 16.7),
    (28, 14.7, 16.5),
    (30, 15.0, 16.7),
    (35, 15.2, 17.5),
    (40, 15.3, 17.4),
    (45, 15.0, 17.4),
    (50, 14.7, 17.9),
]


def _pc_lh_table_bounds(L: float) -> tuple[float, float]:
    """20~50m 查表;中间跨径按相邻标准跨线性插值 L/H 上下限。"""
    eps = 1e-9
    lo_L, lo_low, lo_high = _PC_LH_ANCHORS[0]
    hi_L, hi_low, hi_high = _PC_LH_ANCHORS[-1]
    if L <= lo_L + eps:
        return lo_low, lo_high
    if L >= hi_L - eps:
        return hi_low, hi_high
    for i in range(len(_PC_LH_ANCHORS) - 1):
        L1, low1, high1 = _PC_LH_ANCHORS[i]
        L2, low2, high2 = _PC_LH_ANCHORS[i + 1]
        if L1 - eps <= L <= L2 + eps:
            t = (L - L1) / (L2 - L1)
            return low1 + (low2 - low1) * t, high1 + (high2 - high1) * t
    return hi_low, hi_high


def _d2_thin_soft(lh: float, lh_low: float, lh_high: float) -> tuple[float, str]:
    """表内/13~20m 共用:自由带 [lh_low, lh_high];细高侧 (lh_high, lh_high+1] 线性扣 0~0.25;
    粗于 lh_low 或细于 lh_high+1 扣 1(无粗矮软带)。"""
    eps = 1e-9
    if lh_low - eps <= lh <= lh_high + eps:
        return 0.0, f"L/H={lh_low:.1f}~{lh_high:.1f}(合理)"
    if lh_high + eps < lh <= lh_high + 1.0 + eps:
        ded = _lerp(lh, lh_high, lh_high + 1.0, 0.0, 0.25)
        return ded, f"L/H={lh_high:.1f}~{lh_high + 1:.1f}(偏细高,线性 0~0.25)"
    return 1.0, "L/H 超出合理范围"


def _score_pc_standard_d2(L: float, H: float) -> tuple[float, str, list[float]]:
    """PC 大 T D2 扣分。(deduction, band, expected L/H [low, high])。"""
    eps = 1e-9
    lh = L / H

    if L < 10.0 - eps:
        expected = [11.0, 16.0]
        if 11.0 - eps <= lh <= 16.0 + eps:
            return 0.0, "L/H=11~16(合理)", expected
        if 16.0 + eps < lh <= 17.0 + eps:
            return 0.2, "L/H=16~17(偏细高)", expected
        if 10.0 - eps <= lh < 11.0 - eps:
            return 0.5, "L/H=10~11(偏粗矮)", expected
        return 1.0, "L/H>1/10 或 <1/17", expected

    if L < 13.0 - eps:
        return 1.0, "10~13m(不论梁高)", []

    if L < 20.0 - eps:
        expected = [14.0, 18.0]
        ded, band = _d2_thin_soft(lh, 14.0, 18.0)
        return ded, band, expected

    if L > 50.0 + eps:
        expected = [14.7, 17.9]
        if 14.7 - eps <= lh <= 17.9 + eps:
            return 0.0, "L/H=14.7~17.9(合理)", expected
        if 17.9 + eps < lh <= 18.9 + eps:
            return 0.2, "L/H=17.9~18.9(偏细高)", expected
        if 18.9 + eps < lh <= 19.9 + eps:
            return 0.3, "L/H=18.9~19.9(明显偏细高)", expected
        if 13.7 - eps <= lh < 14.7 - eps:
            return 0.5, "L/H=13.7~14.7(偏粗矮)", expected
        return 1.0, "L/H>1/13.7 或 <1/19.9", expected

    lh_low, lh_high = _pc_lh_table_bounds(L)
    expected = [round(lh_low, 1), round(lh_high, 1)]
    ded, band = _d2_thin_soft(lh, lh_low, lh_high)
    return ded, band, expected


# ---------------------------------------------------------------------------
# D2 高跨比
# ---------------------------------------------------------------------------

def _recip_next(r: float, steps: int = 1) -> float:
    """H/L=1/n → 1/(n+steps)。用于「上限-1」软带。"""
    if r <= 1e-12:
        return r
    return 1.0 / (1.0 / r + steps)


def _low_t_hl_core_band(L: float) -> tuple[float, float]:
    """矮 T 核心高跨比带 [lo, hi]=[最小H/L, 最大H/L](lo 更矮)。"""
    if L < 10.0:
        return (1 / 16, 1 / 11)
    if L < 13.0:
        return (1 / 17, 1 / 12)
    if L < 16.0:
        return (1 / 18, 1 / 15)
    if L < 20.0:
        return (1 / 20, 1 / 16)
    if L < 25.0:
        return (1 / 22, 1 / 16)
    if L <= 30.0:
        return (1 / 21, 1 / 17)
    return (1 / 21, 1 / 18)


def _score_t_girder_d2_height(
    L: float | None,
    H: float | None,
    is_prestressed: bool,
    variant: TVariant = "standard",
) -> tuple[float, dict[str, Any]]:
    """D2 高跨比 H/L(大 T 25%)。

    RC:[1/16,1/13] 不扣;[1/20,1/16) 与 (1/13,1/11] 扣 0.25;更矮或更高扣 1;L>20 不论梁高扣 1。
    PC:标准跨查表,细高侧 1/(下限)~1/(下限+1) 线性扣 0~0.25;13~20m 宜 1/14~1/18;
    <10m / >50m 走专用分档;[10,13) 不论梁高扣 1。
    """
    label = _variant_label(variant)
    system = "PC" if (is_prestressed or variant == "low") else "RC"
    if L is None or H is None or L <= 0 or H <= 0:
        return 0.0, {
            "issue": "L 或 H 缺失,无法核对高跨比",
            "girder_system": system,
            "t_variant": variant,
            "level": "fail",
        }

    ratio = H / L
    deduction = 0.0
    band = ""
    expected_band: list[float]

    if variant == "low":
        lo, hi = _low_t_hl_core_band(L)
        expected_band = [round(lo, 4), round(hi, 4)]
        soft_lo = _recip_next(lo, 1)  # 再矮一档
        soft_hi = 1.0 / (1.0 / hi - 1) if hi < 1 else hi  # 再高一档 1/(n-1)

        if L < 10.0:
            # 特例:<10m 软带与扣分不同
            if 1 / 16 <= ratio <= 1 / 11:
                deduction, band = 0.0, "1/11~1/16(合理)"
            elif 1 / 17 <= ratio < 1 / 16:
                deduction, band = 0.2, "1/16~1/17"
            elif 1 / 11 < ratio <= 1 / 10:
                deduction, band = 0.5, "1/10~1/11"
            else:
                deduction, band = 1.0, ">1/10 或 <1/17"
        elif L > 30.0:
            if 1 / 21 <= ratio <= 1 / 18:
                deduction, band = 0.0, "1/18~1/21(合理)"
            elif 1 / 22 <= ratio < 1 / 21:
                deduction, band = 0.2, "1/21~1/22"
            elif 1 / 18 < ratio <= 1 / 17:
                deduction, band = 0.3, "1/17~1/18"
            elif 1 / 17 < ratio <= 1 / 16:
                deduction, band = 0.5, "1/16~1/17"
            else:
                deduction, band = 1.0, ">1/16 或 <1/22"
        else:
            if lo <= ratio <= hi:
                deduction, band = 0.0, f"{hi:.4f}~{lo:.4f}(合理)"
            elif soft_lo <= ratio < lo:
                deduction, band = 0.25, "略矮一档"
            elif hi < ratio <= soft_hi + 1e-12:
                deduction, band = 0.25, "略高一档"
            else:
                deduction, band = 1.0, "超出允许高跨比"
    elif is_prestressed:
        deduction, band, expected_band = _score_pc_standard_d2(L, H)
    else:
        # RC 大 T:1/13~1/16 不扣;1/11~1/13 与 1/16~1/20 扣 0.25;L>20 不论梁高扣 1
        if L > 20.0 + 1e-9:
            deduction, band = 1.0, "RC 跨径>20m(不论梁高)"
            expected_band = []
        else:
            lh = L / H
            expected_band = [13.0, 16.0]
            if 13.0 - 1e-9 <= lh <= 16.0 + 1e-9:
                deduction, band = 0.0, "L/H=13~16(合理)"
            elif 16.0 + 1e-9 < lh <= 20.0 + 1e-9:
                deduction, band = 0.25, "L/H=16~20(偏细高)"
            elif 11.0 - 1e-9 <= lh < 13.0 - 1e-9:
                deduction, band = 0.25, "L/H=11~13(偏粗矮)"
            else:
                deduction, band = 1.0, "L/H 超出合理范围(>1/11 或 <1/20)"

    score = max(0.0, 1.0 - deduction)
    issue = None
    if score < 1.0 - 1e-9:
        issue = (
            f"{system}简支{label} H/L={ratio:.4f}(H={H}, L={L}) "
            f"落在{band},扣 {deduction:.2f}"
        )

    return score, {
        "H": H,
        "L": L,
        "H_over_L": round(ratio, 4),
        "L_over_H": round(1.0 / ratio, 2) if ratio > 1e-12 else None,
        "girder_system": system,
        "t_variant": variant,
        "expected_band": expected_band,
        "band": band,
        "deduction": deduction,
        "level": level_of(score),
        "issue": issue,
    }


# ---------------------------------------------------------------------------
# D3 截面
# ---------------------------------------------------------------------------

def _low_t_web_band(L: float | None) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    """矮 T 腹板厚:(满分带, 下软带, 上软带)。"""
    if L is None or L < 11.5:
        # 10m 档
        return (0.25, 0.35), (0.22, 0.25), (0.35, 0.40)
    if L < 18.0:
        # 13~16m
        return (0.30, 0.40), (0.25, 0.30), (0.40, 0.40)  # 上软带空: >40 硬扣
    # 20~25m
    return (0.35, 0.45), (0.30, 0.35), (0.45, 0.50)


def _score_t_girder_d3_section(
    mid: dict[str, Any] | None,
    support: dict[str, Any] | None,
    is_prestressed: bool,
    variant: TVariant = "standard",
    L: float | None = None,
) -> tuple[float, dict[str, Any]]:
    """D3 截面常规尺寸(大 T 20%;六小项加权)。

    腹板 20%、翼缘端部 15%、翼缘根部 15%、单侧悬臂 10%、马蹄宽 20%、支点≥跨中 20%。
    """
    label = _variant_label(variant)
    system = "PC" if (is_prestressed or variant == "low") else "RC"
    issues: list[str] = []
    deduction = 0.0
    score: float | None = None
    measures: dict[str, Any] = {"girder_system": system, "t_variant": variant}

    if not mid or mid.get("tw") is None:
        return 0.0, {
            "girder_system": system,
            "t_variant": variant,
            "level": "fail",
            "issues": [f"未能提取 TGIRDER 跨中标准段尺寸(简支{label})"],
            "deduction": 1.0,
            "issue": f"未能提取 TGIRDER 跨中标准段尺寸(简支{label})",
        }

    h = mid.get("h")
    tw = mid.get("tw")
    tt1 = mid.get("tt1")
    tt2 = mid.get("tt2")
    bs = mid.get("bs")
    bm = mid.get("bm")
    bh = mid.get("bh")
    hh = mid.get("hh")
    fillet_x = mid.get("x")  # 翼板倒角宽 → 梗斜
    measures.update({
        "mid_name": mid.get("name"),
        "h": h, "tw": tw, "tt1": tt1, "tt2": tt2, "bs": bs, "bm": bm,
        "bh": bh, "hh": hh, "x": fillet_x,
        "support_name": support.get("name") if support else None,
    })
    assert tw is not None

    if variant == "low":
        # --- 翼缘端部厚 ---
        if tt1 is None:
            deduction += 0.5
            issues.append("翼缘端部厚 tt1 缺失,扣 0.5")
        elif 0.14 <= tt1 <= 0.20:
            pass
        elif 0.12 <= tt1 < 0.14:
            deduction += 0.25
            issues.append(f"翼缘端部厚 tt1={tt1:.3f} m 落在 12~14cm,扣 0.25")
        else:
            deduction += 0.5
            issues.append(f"翼缘端部厚 tt1={tt1:.3f} m 超出 12~20cm,扣 0.5")

        # --- 腹板厚(按跨径) ---
        full, soft_lo, soft_hi = _low_t_web_band(L)
        flo, fhi = full
        if flo <= tw <= fhi:
            pass
        elif soft_lo[0] <= tw < soft_lo[1] or (
            soft_hi[0] < soft_hi[1] and soft_hi[0] < tw <= soft_hi[1]
        ):
            deduction += 0.25
            issues.append(f"腹板厚 tw={tw:.3f} m 落在边缘带,扣 0.25")
        else:
            deduction += 0.5
            issues.append(f"腹板厚 tw={tw:.3f} m 超出矮T允许范围,扣 0.5")

        # --- 梗斜(翼板倒角 x>0) ---
        if fillet_x is None or fillet_x <= 1e-9:
            deduction += 0.5
            issues.append("顶板与腹板间未见梗斜(翼板倒角 x),扣 0.5")

        # 支点腹板不宜小于跨中
        smaller = support_not_smaller(mid, support, ("tw", "h", "tt1", "tt2"))
        if smaller:
            deduction += 1.0
            issues.append("支点段尺寸小于跨中(" + "; ".join(smaller) + "),扣 1.0")
        measures["support"] = {k: (support or {}).get(k) for k in ("tw", "h", "tt1", "tt2")}

    else:
        # ===== 标准 T / 大 T:6 小项加权 =====
        sub: dict[str, float] = {}
        eps = 1e-9

        # 1. 腹板 Tw (20%):16~24cm 不扣;14~16 / 24~25 扣 0.25;否则扣 1;
        #    另 (H-Tt2)/Tw > 30 再扣 0.5,小项封顶 1
        tw_ded = 0.0
        if 0.16 - eps <= tw <= 0.24 + eps:
            pass
        elif 0.14 - eps <= tw < 0.16 - eps or 0.24 + eps < tw <= 0.25 + eps:
            tw_ded += 0.25
            issues.append(f"腹板厚 tw={tw:.3f} m 落在 14~16cm 或 24~25cm,扣 0.25")
        else:
            tw_ded += 1.0
            issues.append(f"腹板厚 tw={tw:.3f} m 超出 14~25cm,扣 1")
        if h is not None and tt2 is not None and tw > 0:
            clear_h = max(0.0, float(h) - float(tt2))
            slenderness = clear_h / float(tw)
            measures["web_clear_h"] = round(clear_h, 4)
            measures["web_slenderness"] = round(slenderness, 2)
            if slenderness > 30.0 + eps:
                tw_ded += 0.5
                issues.append(f"腹板净高/厚度={slenderness:.1f} > 30,扣 0.5")
        sub["web"] = max(0.0, 1.0 - tw_ded)

        # 2. 翼缘端部 Tt1 (15%):15~20cm 不扣;12~15 / 20~22 线性扣 0~0.5;否则扣 1
        if tt1 is None:
            sub["tt1"] = 0.0
            issues.append("翼缘端部厚 tt1 缺失")
        elif 0.15 - eps <= tt1 <= 0.20 + eps:
            sub["tt1"] = 1.0
        elif 0.12 - eps <= tt1 < 0.15 - eps:
            ded = _lerp(tt1, 0.15, 0.12, 0.0, 0.5)
            sub["tt1"] = max(0.0, 1.0 - ded)
            issues.append(f"翼缘端部厚 tt1={tt1:.3f} m 偏薄(12~15cm),扣 {ded:.2f}")
        elif 0.20 + eps < tt1 <= 0.22 + eps:
            ded = _lerp(tt1, 0.20, 0.22, 0.0, 0.5)
            sub["tt1"] = max(0.0, 1.0 - ded)
            issues.append(f"翼缘端部厚 tt1={tt1:.3f} m 偏厚(20~22cm),扣 {ded:.2f}")
        else:
            sub["tt1"] = 0.0
            issues.append(f"翼缘端部厚 tt1={tt1:.3f} m 超出 12~22cm")

        # 3. 翼缘根部 Tt2 (15%):Tt2/H>1/10 且 Tt2>0.22 不扣;
        #    <1/10 或 ≤0.22 扣 1;[1/6,1/5] 扣 0.5;>1/5 扣 1;>0.28 扣 0.5(取严)
        if tt2 is None or h is None or h <= 0:
            sub["tt2"] = 0.0
            issues.append("翼缘根部厚 tt2 或梁高 H 缺失")
        else:
            r = float(tt2) / float(h)
            measures["tt2_over_h"] = round(r, 4)
            ratio_ded = 0.0
            if r < 1.0 / 10.0 - eps:
                ratio_ded = 1.0
                issues.append(f"翼缘根部厚 tt2/H=1/{1.0 / r:.2f} < 1/10")
            elif r > 1.0 / 5.0 + eps:
                ratio_ded = 1.0
                issues.append(f"翼缘根部厚 tt2/H=1/{1.0 / r:.2f} > 1/5")
            elif r >= 1.0 / 6.0 - eps:
                ratio_ded = 0.5
                issues.append(f"翼缘根部厚 tt2/H=1/{1.0 / r:.2f} 落在 1/6~1/5")
            abs_ded = 0.0
            if tt2 <= 0.22 + eps:
                abs_ded = 1.0
                issues.append(f"翼缘根部厚 tt2={tt2:.3f} m ≤ 0.22 m")
            elif tt2 > 0.28 + eps:
                abs_ded = 0.5
                issues.append(f"翼缘根部厚 tt2={tt2:.3f} m > 0.28 m")
            tt2_ded = max(ratio_ded, abs_ded)
            sub["tt2"] = max(0.0, 1.0 - tt2_ded)

        # 4. 单侧悬臂 Bm-Tw/2 (10%):0.6~1.5 不扣;1.5~1.8 扣 0.25;<0.6 或 >1.8 扣 0.5
        if bm is not None and tw > 0:
            cantilever = float(bm) - float(tw) / 2.0
        elif bs is not None:
            cantilever = float(bs)
        else:
            cantilever = None
        measures["cantilever"] = None if cantilever is None else round(cantilever, 4)
        if cantilever is None:
            sub["cantilever"] = 0.0
            issues.append("单侧悬臂(Bm-Tw/2)缺失")
        elif 0.6 - eps <= cantilever <= 1.5 + eps:
            sub["cantilever"] = 1.0
        elif 1.5 + eps < cantilever <= 1.8 + eps:
            sub["cantilever"] = 0.75
            issues.append(f"单侧悬臂 Bm-Tw/2={cantilever:.3f} m 落在 1.5~1.8m,扣 0.25")
        else:
            sub["cantilever"] = 0.5
            issues.append(f"单侧悬臂 Bm-Tw/2={cantilever:.3f} m 超出 0.6~1.8m,扣 0.5")

        # 5. 马蹄宽 Bh (20%):PC 特有;Bh/Tw 2.5~3.5 且 >0.3 不扣;<0.3 扣 0.5;>0.7 扣 1
        if is_prestressed:
            if bh is None:
                sub["horse"] = 0.0
                issues.append("马蹄宽 bh 缺失")
            elif bh > 0.7 + eps:
                sub["horse"] = 0.0
                issues.append(f"马蹄宽 bh={bh:.3f} m > 0.7 m")
            elif bh < 0.3 - eps:
                sub["horse"] = 0.5
                issues.append(f"马蹄宽 bh={bh:.3f} m < 0.3 m")
            else:
                ratio_bh = bh / float(tw) if tw > 0 else None
                measures["bh_over_tw"] = round(ratio_bh, 3) if ratio_bh is not None else None
                if ratio_bh is not None and 2.5 - eps <= ratio_bh <= 3.5 + eps:
                    sub["horse"] = 1.0
                else:
                    sub["horse"] = 0.5
                    issues.append(f"马蹄宽 bh/tw={ratio_bh:.2f} 未落在 2.5~3.5")
        # RC 无马蹄要求,跳过本小项并按剩余权重归一化

        # 6. 支点加厚段 ≥ 跨中 (20%):tt1/tt2/tw/bh/hh 五尺寸
        if support:
            smaller = [k for k in ("tt1", "tt2", "tw", "bh", "hh")
                       if mid.get(k) is not None and support.get(k) is not None
                       and float(support[k]) < float(mid[k]) - eps]
            measures["support"] = {k: support.get(k) for k in ("tt1", "tt2", "tw", "bh", "hh")}
            if smaller:
                sub["support"] = 0.0
                issues.append("支点加厚段尺寸小于跨中(" + "; ".join(smaller) + ")")
            else:
                sub["support"] = 1.0
        else:
            sub["support"] = 1.0
            if is_prestressed:
                issues.append("未识别支点加厚截面,跳过支点≥跨中校核")

        sub_weights = {
            "web": 0.20, "tt1": 0.15, "tt2": 0.15, "cantilever": 0.10,
            "horse": 0.20, "support": 0.20,
        }
        scored = [k for k in sub_weights if k in sub]
        w_sum = sum(sub_weights[k] for k in scored)
        score = sum(sub[k] * sub_weights[k] for k in scored) / w_sum
        deduction = 1.0 - score
        measures["sub_scores"] = sub
        measures["sub_weights"] = {k: sub_weights[k] for k in scored}
    if score is None:  # 矮T 分支走累加扣分
        score = max(0.0, 1.0 - deduction)
    return score, {
        **measures,
        "deduction": round(deduction, 3),
        "level": level_of(score),
        "issues": issues,
        "issue": issues[0] if issues else None,
    }


# ---------------------------------------------------------------------------
# D4 经济性(混凝土折算厚度 + 钢绞线用量,各 50%)
# ---------------------------------------------------------------------------

def _score_t_girder_d4_economy(
    concrete_ratio: float | None,
    pst_steel_ratio: float | None,
    variant: TVariant = "standard",
    is_prestressed: bool = True,
) -> tuple[float, dict[str, Any]]:
    """D4 建设期经济性(大 T 20%;两项各占 50%)。

    大 T:折算厚度 [0.35,0.65] 不扣,(0.65,0.75] 扣 0.5,其余扣 1;
    钢绞线 [30,50] 不扣,[24,30) 扣 0.3,(50,60] 线性扣 0~1,其余扣 1。RC 无钢绞线则跳过该小项。
    """
    issues: list[str] = []
    sub: dict[str, float] = {}
    eps = 1e-9

    if variant == "low":
        # 矮 T 暂沿用既有分档,待矮 T D4 准则到位后再切
        if concrete_ratio is None:
            sub["concrete"] = 0.0
            issues.append("未能提取混凝土折算厚度")
        elif 0.35 - eps <= concrete_ratio <= 0.65 + eps:
            sub["concrete"] = 1.0
        elif 0.65 + eps < concrete_ratio <= 0.75 + eps:
            ded = 5.0 * (concrete_ratio - 0.65)
            sub["concrete"] = 1.0 - ded
            issues.append(f"混凝土折算厚度 {concrete_ratio:.4f} 偏大(0.65~0.75),扣 {ded:.2f}")
        elif 0.20 - eps <= concrete_ratio < 0.35 - eps:
            ded = 0.5 * (0.35 - concrete_ratio) / 0.15
            sub["concrete"] = 1.0 - ded
            issues.append(f"混凝土折算厚度 {concrete_ratio:.4f} 偏小(0.20~0.35),扣 {ded:.2f}")
        else:
            sub["concrete"] = 0.0
            issues.append(f"混凝土折算厚度 {concrete_ratio:.4f} 超出 0.20~0.75")
        if pst_steel_ratio is None:
            sub["steel"] = 0.0
            issues.append("未能提取预应力钢绞线用量")
        elif 30 - eps <= pst_steel_ratio <= 50 + eps:
            sub["steel"] = 1.0
        elif 24 - eps <= pst_steel_ratio < 30 - eps:
            ded = 0.3 * (30 - pst_steel_ratio) / 6.0
            sub["steel"] = 1.0 - ded
            issues.append(f"钢绞线用量 {pst_steel_ratio:.1f} kg/m³ 偏低(24~30),扣 {ded:.2f}")
        elif 50 + eps < pst_steel_ratio <= 60 + eps:
            ded = 0.3 * (pst_steel_ratio - 50) / 10.0
            sub["steel"] = 1.0 - ded
            issues.append(f"钢绞线用量 {pst_steel_ratio:.1f} kg/m³ 偏高(50~60),扣 {ded:.2f}")
        else:
            sub["steel"] = 0.0
            issues.append(f"钢绞线用量 {pst_steel_ratio:.1f} kg/m³ 超出 24~60")
    else:
        # 1. 混凝土折算厚度 50%:0.35~0.65 不扣;0.65~0.75 扣 0.5;其余扣 1
        if concrete_ratio is None:
            sub["concrete"] = 0.0
            issues.append("未能提取混凝土折算厚度")
        elif 0.35 - eps <= concrete_ratio <= 0.65 + eps:
            sub["concrete"] = 1.0
        elif 0.65 + eps < concrete_ratio <= 0.75 + eps:
            sub["concrete"] = 0.5
            issues.append(f"混凝土折算厚度 {concrete_ratio:.4f} 偏大(0.65~0.75),扣 0.50")
        else:
            sub["concrete"] = 0.0
            issues.append(f"混凝土折算厚度 {concrete_ratio:.4f} 超出 0.35~0.75,扣 1")

        # 2. 预应力钢绞线 50%:30~50 不扣;24~30 扣 0.3;50~60 线性扣 0~1。RC 跳过
        if not is_prestressed:
            pass
        elif pst_steel_ratio is None:
            sub["steel"] = 0.0
            issues.append("未能提取预应力钢绞线用量")
        elif 30.0 - eps <= pst_steel_ratio <= 50.0 + eps:
            sub["steel"] = 1.0
        elif 24.0 - eps <= pst_steel_ratio < 30.0 - eps:
            sub["steel"] = 0.7
            issues.append(f"钢绞线用量 {pst_steel_ratio:.1f} kg/m³ 偏低(24~30),扣 0.30")
        elif 50.0 + eps < pst_steel_ratio <= 60.0 + eps:
            ded = (pst_steel_ratio - 50.0) / 10.0
            sub["steel"] = 1.0 - ded
            issues.append(f"钢绞线用量 {pst_steel_ratio:.1f} kg/m³ 偏高(50~60),扣 {ded:.2f}")
        else:
            sub["steel"] = 0.0
            issues.append(f"钢绞线用量 {pst_steel_ratio:.1f} kg/m³ 超出 24~60,扣 1")

    weights = {"concrete": 0.5, "steel": 0.5}
    scored = [k for k in weights if k in sub]
    if not scored:
        score = 1.0
        issues.append("无经济性数据,D4 跳过给 1.0")
    else:
        w_sum = sum(weights[k] for k in scored)
        score = sum(sub[k] * weights[k] for k in scored) / w_sum
    return score, {
        "concrete_ratio": None if concrete_ratio is None else round(concrete_ratio, 4),
        "pst_steel_ratio": None if pst_steel_ratio is None else round(pst_steel_ratio, 3),
        "t_variant": variant,
        "sub_scores": sub,
        "level": level_of(score),
        "issues": issues,
        "issue": issues[0] if issues else None,
        "deduction": round(1.0 - score, 3),
    }


def _score_t_girder_d5_standardization(
    beam_width: float | None,
    stage_count: int,
    stage_names: list[str] | None,
    variant: TVariant = "standard",
) -> tuple[float, dict[str, Any]]:
    """D5 标准化(大 T 10%;梁宽 50% + 施工阶段 50%)。

    大 T:梁宽 [1.6,2.3] 不扣,越界扣 1;施工阶段须含预制/存梁/二期/徐变且 ≥4,否则扣 1。
    矮 T:梁宽 [1.0,1.55] 不扣,越界扣 1;施工阶段规则同大 T。
    """
    issues: list[str] = []
    sub: dict[str, float] = {}
    eps = 1e-9
    names = list(stage_names or [])
    blob = "".join(names)
    missing = [k for k in ("预制", "存梁", "二期", "徐变") if k not in blob]

    if variant == "low":
        if beam_width is None:
            sub["width"] = 0.0
            issues.append("未能提取梁宽/梁间距")
        elif 1.0 - eps <= beam_width <= 1.55 + eps:
            sub["width"] = 1.0
        else:
            sub["width"] = 0.0
            issues.append(f"梁宽 {beam_width:.3f} m 小于 1.0 m 或大于 1.55 m,扣 0.5")
        if stage_count >= 4 and not missing:
            sub["stage"] = 1.0
        else:
            sub["stage"] = 0.0
            if stage_count < 4:
                issues.append(f"施工阶段数 {stage_count} < 4")
            if missing:
                issues.append("施工阶段缺少「" + "、".join(missing) + "」")
    else:
        # 1. 梁宽 50%:<1.6 或 >2.3 扣 1
        if beam_width is None:
            sub["width"] = 0.0
            issues.append("未能提取梁宽/梁间距")
        elif 1.6 - eps <= beam_width <= 2.3 + eps:
            sub["width"] = 1.0
        else:
            sub["width"] = 0.0
            issues.append(f"梁宽 {beam_width:.3f} m 小于 1.6 m 或大于 2.3 m,扣 1")

        # 2. 施工阶段 50%:须含预制/存梁/二期/徐变且至少 4 个,否则扣 1
        if stage_count >= 4 and not missing:
            sub["stage"] = 1.0
        else:
            sub["stage"] = 0.0
            if stage_count < 4:
                issues.append(f"施工阶段数 {stage_count} < 4,扣 1")
            if missing:
                issues.append("施工阶段缺少「" + "、".join(missing) + "」,扣 1")

    score = sub["width"] * 0.5 + sub["stage"] * 0.5
    return score, {
        "beam_width": None if beam_width is None else round(beam_width, 4),
        "stage_count": stage_count, "stage_names": names,
        "t_variant": variant,
        "sub_scores": sub,
        "level": level_of(score),
        "issues": issues,
        "issue": issues[0] if issues else None,
        "deduction": round(1.0 - score, 3),
    }


def score_t_girder(params: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """入口:按马蹄自动分流标准 T / 矮 T。"""
    pc = is_pc(params)
    L, H = params.get("L"), params.get("H_root")
    mid = params.get("t_girder_mid")
    variant = _detect_t_variant(mid)
    # 折算厚度优先 A_avg/梁宽;钢绞线用线密度/A_avg
    area = params.get("section_area_avg")
    if area is None and mid is not None:
        area = _tgirder_section_area(mid)
    beam_width = params.get("beam_width")
    concrete_ratio = params.get("concrete_ratio")
    if (
        concrete_ratio is None
        and area is not None
        and beam_width is not None
        and float(beam_width) > 1e-12
    ):
        concrete_ratio = float(area) / float(beam_width)
    steel_ratio = params.get("pst_steel_ratio")
    if steel_ratio is None:
        steel_ratio = _pst_steel_ratio_kg_m3(
            params.get("pst_steel_kg_per_m"), area,
        )
    dims = [
        ("D1_span", *_score_t_girder_d1_span(L, pc, variant)),
        ("D2_beam_height", *_score_t_girder_d2_height(L, H, pc, variant)),
        ("D3_section", *_score_t_girder_d3_section(
            mid, params.get("t_girder_support"), pc, variant, L,
        )),
        ("D4_economy", *_score_t_girder_d4_economy(
            concrete_ratio, steel_ratio, variant, pc,
        )),
        ("D5_standardization", *_score_t_girder_d5_standardization(
            beam_width,
            int(params.get("stage_count") or 0), params.get("stage_names") or [],
            variant,
        )),
    ]
    weights = {"D1_span": 0.25, "D2_beam_height": 0.25, "D3_section": 0.20,
               "D4_economy": 0.20, "D5_standardization": 0.10}
    overall, details = _assemble(params, dims, weights=weights)
    details["t_variant"] = variant
    return overall, details
