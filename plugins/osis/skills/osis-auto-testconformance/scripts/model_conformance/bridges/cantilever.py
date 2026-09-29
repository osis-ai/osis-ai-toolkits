"""Cantilever box / variable-section bridge scoring (MD D1-D5)."""
from __future__ import annotations

import math
from typing import Any

from ..common import _L_VALID, _assemble, _lerp, _level_from_score


def _expected_h_mid(L: float) -> tuple[float | None, float, str]:
    """跨中梁高理论值与容差(MD §4.2)。返回 (expected, tolerance, range_str)。"""
    if 60 <= L < 92.4:
        return 2.2, 0.10, "[2.2, 2.3]"
    if 92.4 <= L < 100:
        v = max(L / 42, 2.2)
        return v, 0.10, f"[{v - 0.05:.4f}, {v + 0.05:.4f}]"
    if 100 <= L < 150:
        v = L / 40
        return v, 0.10, f"[{v - 0.05:.4f}, {v + 0.05:.4f}]"
    if 150 <= L <= 200:
        v = L / 38
        return v, 0.10, f"[{v - 0.05:.4f}, {v + 0.05:.4f}]"
    return None, 0.0, ""


def _n_h_band(L: float) -> tuple[float, float, float]:
    """梁高变化指数优先值与区间(MD §4.3)。返回 (preferred, low, high)。"""
    if 60 <= L < 100:
        return 2.0, 2.0, 2.0
    if 100 <= L < 150:
        return 1.8, 1.8, 1.8
    if 150 <= L <= 200:
        return 1.8, 1.5, 1.8
    return 0.0, 0.0, 0.0
# ---- 变截面曲线指数:理论曲线匹配(替代旧 log 回归拟合)----

def _candidate_n_values() -> list[float]:
    """待匹配的 n 候选:1.40~2.50,步长 0.05(覆盖各跨径分档)。"""
    vals: list[float] = []
    n = 1.40
    while n <= 2.50 + 1e-9:
        vals.append(round(n, 2))
        n += 0.05
    return vals


def _plateau_tol(h_root: float, h_mid: float) -> float:
    """等截面段判定容差(m)。过松会把曲线尾部吃进跨中平台,导致 n 偏低。"""
    return max(0.001, 0.0005 * abs(h_root - h_mid))


def _root_station(pts: list[tuple[float, float]], h_max: float, tol: float) -> float:
    """根部桩号:取 h≈h_max 最长连续簇的中点。

    若取「第一个最大值点」,会落到根部等截面平台左端,虚增 X_H,匹配 n 系统性偏低。
    """
    xs = [x for x, h in pts if abs(h - h_max) <= tol]
    if not xs:
        return next(x for x, h in pts if h == h_max)
    xs = sorted(xs)
    dxs = [pts[i + 1][0] - pts[i][0] for i in range(len(pts) - 1)]
    dxs = [d for d in dxs if d > 1e-9]
    gap = 1.5 * (sorted(dxs)[len(dxs) // 2] if dxs else 1.0)
    clusters: list[list[float]] = [[xs[0]]]
    for x in xs[1:]:
        if x - clusters[-1][-1] <= gap + 1e-9:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    best = max(clusters, key=len)
    return 0.5 * (best[0] + best[-1])


def _fit_height_exponent(
    profile: list[tuple[float, float]],
    L: float,
) -> tuple[float | None, dict[str, Any]]:
    """从 (x, h) 匹配变截面梁高曲线指数 n_H。

    剖面应为单元两端节点处截面高(非单元中点挂 nSec1)。在变化段各桩号 s 上,
    对候选 n 生成理论梁高
        H(s,n) = H_mid + (H_root - H_mid) * u^n
        u = (curve_end - s) / (curve_end - X_H)
    取与模型梁高 RMSE 最小的 n 作为 n_H。

    几何预处理(区分平直段/变化段,对应测试标注的红/绿):
      1. 根部 = h≈h_max 最长簇中点;取半跨并转到 s=0 在根部
      2. 根部/跨中等截面平直段 → X_H、curve_end(红段不进 RMSE)
      3. 仅在变化段(绿段)内做曲线匹配

    返 (n_H, detail)。失败返 (None, detail)。
    """
    detail: dict[str, Any] = {}
    if L is None or L <= 0:
        return None, {"issue": "L 缺失"}
    if len(profile) < 5:
        return None, {"issue": f"数据点不足({len(profile)} < 5)"}

    by_x: dict[float, list[float]] = {}
    for x, h in profile:
        by_x.setdefault(round(x, 3), []).append(h)
    pts: list[tuple[float, float]] = sorted(
        ((x, sum(hs) / len(hs)) for x, hs in by_x.items()),
        key=lambda p: p[0],
    )
    if len(pts) < 5:
        return None, {"issue": "去重后数据点不足"}

    h_max = max(h for _, h in pts)
    h_min = min(h for _, h in pts)
    if h_max <= h_min + 0.01:
        return None, {"issue": "非变截面(h_max ≈ h_min)"}

    eps = _plateau_tol(h_max, h_min)
    x_root = _root_station(pts, h_max, eps)

    half_L = L / 2.0
    left_side = [(x, h) for x, h in pts if x <= x_root]
    right_side = [(x, h) for x, h in pts if x >= x_root]
    if len(right_side) >= len(left_side):
        half_pts = [(x - x_root, h) for x, h in right_side]
    else:
        half_pts = [(x_root - x, h) for x, h in left_side]
    half_pts = [(s, h) for s, h in half_pts if 0 <= s <= half_L + 1.0]
    half_pts.sort(key=lambda p: p[0])
    if len(half_pts) < 5:
        return None, {"issue": "半跨数据点不足"}

    x_h = 0.0
    for s, h in half_pts:
        if abs(h - h_max) <= eps:
            x_h = s
        else:
            break
    # 跨中平台:取 h≈h_min 的最长连续段,以其起点为曲线终点。
    # 非对称三跨(如 95+180+195)从主墩往较短跨取半跨时,剖面会越过该跨跨中、
    # 混入下一主墩的上升段;若简单从末尾回退,曲线终点被错误延后,
    # 曲线长度虚增,设计 1.8 会被拟成 2.05。
    runs: list[tuple[float, float]] = []
    run_start: float | None = None
    run_end: float | None = None
    for s, h in half_pts:
        if abs(h - h_min) <= eps:
            if run_start is None:
                run_start = s
            run_end = s
        elif run_start is not None:
            runs.append((run_start, run_end))
            run_start = None
    if run_start is not None:
        runs.append((run_start, run_end))
    best_run = max(runs, key=lambda r: r[1] - r[0]) if runs else None
    curve_end_s = best_run[0] if best_run else half_pts[-1][0]

    if curve_end_s <= x_h + 0.5:
        return None, {"issue": f"变化段长度非正(X_H={x_h}, end={curve_end_s})"}

    var_points = [(s, h) for s, h in half_pts if x_h < s < curve_end_s]
    if len(var_points) < 3:
        return None, {"issue": f"变化段内点不足({len(var_points)} < 3)"}

    # 用平台段均值作端点梁高,减轻单点噪声;跨中端只取最长平台段内点
    # (非对称三跨跨中平台之后还有下一主墩的上升段,不能混入)
    root_hs = [h for s, h in half_pts if s <= x_h + 1e-9]
    if best_run is not None:
        mid_hs = [
            h for s, h in half_pts if best_run[0] - 1e-9 <= s <= best_run[1] + 1e-9
        ]
    else:
        mid_hs = [h for s, h in half_pts if s >= curve_end_s - 1e-9]
    h_root = (sum(root_hs) / len(root_hs)) if root_hs else h_max
    h_mid = (sum(mid_hs) / len(mid_hs)) if mid_hs else h_min

    span = curve_end_s - x_h
    best_n: float | None = None
    best_rmse = float("inf")
    best_mae = float("inf")
    for n in _candidate_n_values():
        sq = 0.0
        abs_err = 0.0
        ok = 0
        for s, h in var_points:
            u = (curve_end_s - s) / span
            if not (0.0 < u < 1.0):
                continue
            h_th = h_mid + (h_root - h_mid) * (u ** n)
            d = h - h_th
            sq += d * d
            abs_err += abs(d)
            ok += 1
        if ok < 3:
            continue
        rmse = math.sqrt(sq / ok)
        mae = abs_err / ok
        if rmse < best_rmse - 1e-12 or (
            abs(rmse - best_rmse) <= 1e-12 and best_n is not None and n < best_n
        ):
            best_rmse = rmse
            best_mae = mae
            best_n = n

    if best_n is None:
        return None, {"issue": "曲线匹配无有效候选"}

    detail.update({
        "method": "curve_match",
        "h_root": round(h_root, 4),
        "h_mid": round(h_mid, 4),
        "X_H": round(x_h, 4),
        "curve_end_x": round(curve_end_s, 4),
        "n_H_matched": round(best_n, 4),
        "n_H_fitted": round(best_n, 4),  # 兼容旧报告字段名
        "rmse_m": round(best_rmse, 5),
        "mae_m": round(best_mae, 5),
        "var_points": len(var_points),
        "x_root": round(x_root, 4),
        "plateau_tol_m": round(eps, 5),
    })
    return best_n, detail


# ---- D1 支点梁高(占比 20%):分跨高跨比区间 + 偏差分段扣分 ----
# 纯悬浇连续梁经济跨径多在 120m 内,兼顾安全通常 ≤160m,极端可达 170m;
# 无墩分担弯矩,支点高跨比通常比同跨径刚构更激进。
# 非表列跨径向下取档(如 100~110m 取 100m 的 1/16.1~1/18.9);
# 50m 以下用 50m 档,170m 以上用 170m 档。
#
# (标准跨径 m, 区间下限分母 lo_den, 区间上限分母 hi_den)
# 允许高跨比区间 = [1/lo_den, 1/hi_den];准则原文写作「1/hi_den~1/lo_den」
# 主梁全高 h 列为该标准跨径下由高跨比反算的参考梁高,评分用 H_root/L。
_D1_RATIO_TABLE: tuple[tuple[float, float, float], ...] = (
    (50.0, 16.7, 15.0),     # h 3.1~3.3
    (60.0, 17.2, 15.0),     # h 3.5~4
    (70.0, 18.0, 15.5),     # h 3.8~4.5
    (80.0, 18.61, 16.0),    # h 4.3~5
    (90.0, 19.15, 16.3),    # h 4.7~5.5
    (100.0, 18.9, 16.1),    # h 5.3~6.2
    (110.0, 18.97, 15.94),  # h 5.8~6.9
    (120.0, 19.4, 16.0),    # h 6.2~7.5
    (130.0, 19.2, 16.25),   # h 6.8~8
    (140.0, 19.2, 16.6),    # h 7.3~8.4
    (150.0, 20.0, 17.0),    # h 7.5~8.8
    (160.0, 20.5, 17.2),    # h 7.8~9.3
    (170.0, 20.0, 17.7),    # h 8.5~9.6
)

# 偏差(高跨比绝对差)分段扣分阈值
_D1_TOL1, _D1_TOL2, _D1_TOL3 = 1.0 / 1500.0, 1.0 / 500.0, 1.0 / 100.0


def _d1_ratio_band(L: float) -> tuple[float, float, float, float, float]:
    """按 L 查高跨比允许区间。返回 (lo, hi, 标准跨径档, lo_den, hi_den)。

    非表列跨径向下取最近标准跨径档(如 100~110m 取 100m 档);
    50m 以下用 50m 档,170m 以上用 170m 档。
    """
    row = _D1_RATIO_TABLE[0]
    for r in _D1_RATIO_TABLE:
        if L >= r[0]:
            row = r
        else:
            break
    std, lo_den, hi_den = row
    return 1.0 / lo_den, 1.0 / hi_den, std, lo_den, hi_den


def _score_md_d1(L: float | None, H_root: float | None) -> tuple[float, dict[str, Any]]:
    """支点(根部)梁高 H_root 评分(新准则:分跨高跨比区间,占比 20%)。

    规则:
      - 按主跨 L 查「标准跨径 → 高跨比允许区间」表,得 r = H_root/L 的允许区间
      - r 在区间内:不扣分(得分 1.0)
      - 超出区间的偏差 d(高跨比绝对差)分段扣分:
          0 < d <= 1/1500: 扣分 0 → 0.2 线性插值
          1/1500 < d <= 1/500: 扣分 0.2 → 0.8 线性插值
          1/500 < d <= 1/100: 扣分 0.8 → 1.0 线性插值
          d > 1/100: 扣 1 分(得分 0)
    """
    if L is None:
        return 0.0, {"issue": "L 缺失,无法核对根部梁高"}
    if L <= 0:
        return 0.0, {"issue": f"L={L} 非法,无法核对根部梁高"}
    if H_root is None:
        return 0.0, {"issue": "H_root 缺失"}

    lo, hi, std, lo_den, hi_den = _d1_ratio_band(L)
    r = H_root / L
    band_str = f"1/{hi_den:g} ~ 1/{lo_den:g}"
    ratio_str = f"1/{L / H_root:.2f}" if H_root > 0 else "∞"

    if r < lo:
        d = lo - r
    elif r > hi:
        d = r - hi
    else:
        d = 0.0

    if d <= 0.0:
        deduction = 0.0
    elif d <= _D1_TOL1:
        deduction = _lerp(d, 0.0, _D1_TOL1, 0.0, 0.2)
    elif d <= _D1_TOL2:
        deduction = _lerp(d, _D1_TOL1, _D1_TOL2, 0.2, 0.8)
    elif d <= _D1_TOL3:
        deduction = _lerp(d, _D1_TOL2, _D1_TOL3, 0.8, 1.0)
    else:
        deduction = 1.0
    score = max(0.0, 1.0 - deduction)
    level = _level_from_score(score)

    issue = None
    if deduction > 1e-9:
        issue = (
            f"高跨比 {ratio_str} 超出允许区间 {band_str}"
            f"(按 {std:g}m 跨档,偏差 {d:.5f},扣分 {deduction:.2f})"
        )
    return score, {
        "actual": H_root,
        "ratio": ratio_str,
        "allowed_range": band_str,
        "expected_band": band_str,
        "std_span": std,
        "deduction": round(deduction, 4),
        "level": level,
        "issue": issue,
    }


# ---- D2 跨中梁高(占比 15%):分跨高跨比区间 + 偏差分段扣分 ----
# 连续梁跨中下挠控制与刚构接近,但无墩身约束、徐变更大,通常取偏保守高跨比;
# 同跨径下连续梁跨中梁高显著更高、梁高变化幅度更小。
# 非表列跨径向下取档(如 110~120m 取 110m 的 1/34.375~1/40.74);
# 50m 以下用 50m 档,170m 以上用 170m 档;L<70 且 H∈[1.8,2) 只扣 0.5。
#
# (标准跨径 m, 区间下限分母 lo_den, 区间上限分母 hi_den)
# 允许高跨比区间 = [1/lo_den, 1/hi_den];准则原文写作「1/hi_den~1/lo_den」
# 梁高 H 列为该标准跨径下由高跨比反算的参考梁高,评分用 H_mid/L。
_D2_RATIO_TABLE: tuple[tuple[float, float, float], ...] = (
    (50.0, 25.0, 22.7),     # h 2~2.2
    (60.0, 30.0, 27.2),     # h 2~2.2
    (70.0, 35.0, 29.16),    # h 2~2.4
    (80.0, 36.4, 32.0),     # h 2.2~2.5
    (90.0, 40.91, 33.33),   # h 2.2~2.7
    (100.0, 41.67, 33.33),  # h 2.4~3
    (110.0, 40.74, 34.375), # h 2.7~3.2
    (120.0, 40.0, 35.29),   # h 3~3.4
    (130.0, 42.0, 36.1),    # h 3.1~3.6
    (140.0, 42.5, 36.8),    # h 3.3~3.8
    (150.0, 42.9, 36.5),    # h 3.5~4.1
    (160.0, 44.5, 36.0),    # h 3.6~4.4
    (170.0, 44.74, 36.0),   # h 3.8~4.7
)

# 偏差(高跨比绝对差)分段扣分阈值
_D2_TOL1, _D2_TOL2, _D2_TOL3 = 1.0 / 1000.0, 1.0 / 500.0, 1.0 / 100.0


def _d2_ratio_band(L: float) -> tuple[float, float, float, float, float]:
    """按 L 查跨中高跨比允许区间。返回 (lo, hi, 标准跨径档, lo_den, hi_den)。

    非表列跨径向下取最近标准跨径档(如 110~120m 取 110m 档);
    50m 以下用 50m 档,170m 以上用 170m 档。
    """
    row = _D2_RATIO_TABLE[0]
    for r in _D2_RATIO_TABLE:
        if L >= r[0]:
            row = r
        else:
            break
    std, lo_den, hi_den = row
    return 1.0 / lo_den, 1.0 / hi_den, std, lo_den, hi_den


def _score_md_d2(L: float | None, H_mid: float | None) -> tuple[float, dict[str, Any]]:
    """跨中梁高 H_mid 评分(新准则:分跨高跨比区间,占比 15%)。

    规则:
      - 按主跨 L 查「标准跨径 → 高跨比允许区间」表,得 r = H_mid/L 的允许区间
      - r 在区间内:不扣分(得分 1.0)
      - 特殊档:L < 70m 且 H_mid ∈ [1.8, 2.0) m,只扣 0.5 分
      - 其余按超出区间的偏差 d(高跨比绝对差)分段扣分:
          0 < d <= 1/1000: 扣分 0 → 0.2 线性插值
          1/1000 < d <= 1/500: 扣分 0.2 → 0.8 线性插值
          1/500 < d <= 1/100: 扣分 0.8 → 1.0 线性插值
          d > 1/100: 扣 1 分(得分 0)
    """
    if L is None:
        return 0.0, {"issue": "L 缺失,无法核对跨中梁高"}
    if L <= 0:
        return 0.0, {"issue": f"L={L} 非法,无法核对跨中梁高"}
    if H_mid is None:
        return 0.0, {"issue": "H_mid 缺失"}

    lo, hi, std, lo_den, hi_den = _d2_ratio_band(L)
    r = H_mid / L
    band_str = f"1/{hi_den:g} ~ 1/{lo_den:g}"
    ratio_str = f"1/{L / H_mid:.2f}" if H_mid > 0 else "∞"

    if r < lo:
        d = lo - r
    elif r > hi:
        d = r - hi
    else:
        d = 0.0

    special = False
    if d <= 0.0:
        deduction = 0.0
    elif L < 70.0 and 1.8 <= H_mid < 2.0:
        # 特殊档:70m 以下跨径梁高在 [1.8, 2) m,只扣 0.5 分
        deduction = 0.5
        special = True
    elif d <= _D2_TOL1:
        deduction = _lerp(d, 0.0, _D2_TOL1, 0.0, 0.2)
    elif d <= _D2_TOL2:
        deduction = _lerp(d, _D2_TOL1, _D2_TOL2, 0.2, 0.8)
    elif d <= _D2_TOL3:
        deduction = _lerp(d, _D2_TOL2, _D2_TOL3, 0.8, 1.0)
    else:
        deduction = 1.0
    score = max(0.0, 1.0 - deduction)
    level = _level_from_score(score)

    issue = None
    if special:
        issue = f"跨中梁高 {H_mid} m 在 [1.8, 2) m(L={L:g}m<70m 特殊档,扣 0.5 分)"
    elif deduction > 1e-9:
        issue = (
            f"高跨比 {ratio_str} 超出允许区间 {band_str}"
            f"(按 {std:g}m 跨档,偏差 {d:.5f},扣分 {deduction:.2f})"
        )
    return score, {
        "actual": H_mid,
        "ratio": ratio_str,
        "allowed_range": band_str,
        "expected_band": band_str,
        "std_span": std,
        "deduction": round(deduction, 4),
        "level": level,
        "issue": issue,
    }


def _d3_deduction(L: float, n: float) -> tuple[float, str, float | None]:
    """按 L 分档 + 幂次 n 给扣分(占比 15%)。返回 (扣分, 档标签, 优值或 None)。

    悬浇段梁高变化曲线。50~90m 首选 2.0 次;90~150m 首选 1.8~2.0 次。
    分档(B/C 在 L=100 重叠时取更高分档 C):
      A. [50,70)(L<50 同档):n ∈ [1,3] 不扣,否则扣 1
      B. [70,100]:优选 2(1.8 不扣);[1.5,1.8)&(2,3] 扣 0.5;(-∞,1.5)&(3,+∞) 扣 1
      C. [100,150]:优选 1.8(2 不扣);(2,3] 扣 0.5;(-∞,1.5)&(3,+∞) 扣 1
      D. (150,170]:优选 1.5;(1.8,2] 扣 0.1;[1.4,1.5) 扣 0.25;(-∞,1.4)&(2,+∞) 扣 1
      E. (170,200]:优选 1.5;[1.4,1.5) 扣 0.1;(1.8,2] 扣 0.25;(-∞,1.4)&(2,+∞) 扣 1
      F. (200,+∞]:任意幂次扣 1
    """
    eps = 1e-9
    if L > 200.0:
        return 1.0, "F((200,+∞])", None
    if L < 70.0:  # A 档(L<50 同按「跨度太小」处理)
        if 1.0 - eps <= n <= 3.0 + eps:
            return 0.0, "A([50,70))", None
        return 1.0, "A([50,70))", None
    if L < 100.0:  # B 档 [70,100];L=100 归 C
        if n < 1.5 - eps or n > 3.0 + eps:
            return 1.0, "B([70,100])", 2.0
        if (1.5 - eps <= n < 1.8 - eps) or (2.0 + eps < n <= 3.0 + eps):
            return 0.5, "B([70,100])", 2.0
        return 0.0, "B([70,100])", 2.0
    if L <= 150.0:  # C 档 [100,150]
        if n < 1.5 - eps or n > 3.0 + eps:
            return 1.0, "C([100,150])", 1.8
        if 2.0 + eps < n <= 3.0 + eps:
            return 0.5, "C([100,150])", 1.8
        return 0.0, "C([100,150])", 1.8
    if L <= 170.0:  # D 档
        if n < 1.4 - eps or n > 2.0 + eps:
            return 1.0, "D((150,170])", 1.5
        if 1.4 - eps <= n < 1.5 - eps:
            return 0.25, "D((150,170])", 1.5
        if 1.8 + eps < n <= 2.0 + eps:
            return 0.1, "D((150,170])", 1.5
        return 0.0, "D((150,170])", 1.5
    # E 档 (170,200]
    if n < 1.4 - eps or n > 2.0 + eps:
        return 1.0, "E((170,200])", 1.5
    if 1.4 - eps <= n < 1.5 - eps:
        return 0.1, "E((170,200])", 1.5
    if 1.8 + eps < n <= 2.0 + eps:
        return 0.25, "E((170,200])", 1.5
    return 0.0, "E((170,200])", 1.5


def _score_md_d3(
    L: float | None,
    height_profile: list[tuple[float, float]] | None = None,
) -> tuple[float, dict[str, Any]]:
    """n_H:悬浇段梁高变化曲线幂次评分(分跨分档扣分,占比 15%)。

    适用对象:悬浇连续梁;刚构走 rigid_frame.py。
    无剖面或匹配失败给 0.5 中性分(不破坏总分结构)。
    """
    if L is None:
        return 0.0, {"issue": "L 缺失,无法核对梁高曲线指数"}
    if L <= 0:
        return 0.0, {"issue": f"L={L} 非法,无法核对梁高曲线指数"}
    if not height_profile:
        return 0.5, {
            "level": "neutral",
            "note": "n_H 匹配失败(无 height_profile),暂给 0.5 中性分",
        }

    n_H, fit_detail = _fit_height_exponent(height_profile, L)
    if n_H is None:
        return 0.5, {
            "level": "neutral",
            "note": f"n_H 匹配失败({fit_detail.get('issue', '未知')}),暂给 0.5 中性分",
            "fit_detail": fit_detail,
        }

    deduction, band, preferred = _d3_deduction(L, n_H)
    score = max(0.0, 1.0 - deduction)
    level = _level_from_score(score)

    issue = None
    if deduction > 1e-9:
        pref = f"优值 {preferred} 次" if preferred is not None else "无优值"
        issue = f"n_H={n_H:.2f} 在 {band} 档扣分 {deduction:.2f}({pref})"
    return score, {
        "expected_band": band,
        "preferred": preferred,
        "actual": round(n_H, 4),
        "deduction": round(deduction, 4),
        "level": level,
        "issue": issue,
        "fit_detail": fit_detail,
    }


def _is_thickness_trend_ok(profile: list[tuple[float, float]]) -> bool:
    """检查底板厚度沿 x 呈 U 形:跨中(最小)向两侧支点单调增大。"""
    if len(profile) < 3:
        return True
    sorted_profile = sorted(profile, key=lambda p: p[0])
    t_values = [tb for _, tb in sorted_profile]
    # 多跨桥边跨现浇段底板也薄,全局最小值常落在边跨而非主跨跨中,
    # 直接做全桥 U 形检查会误判 → 截取最外侧两个支点峰之间的主跨区间。
    peak = max(t_values)
    peak_idx = [i for i, v in enumerate(t_values) if v >= peak - 1e-9]
    lo, hi = peak_idx[0], peak_idx[-1]
    seg = t_values[lo:hi + 1] if hi > lo else t_values
    min_idx = seg.index(min(seg))
    # 左侧:从支点到跨中应单调不增
    for i in range(min_idx):
        if seg[i] < seg[i + 1]:
            return False
    # 右侧:从跨中到支点应单调不减
    for i in range(min_idx, len(seg) - 1):
        if seg[i] > seg[i + 1]:
            return False
    return True


# ---- D4 截面常规尺寸(新准则,仅悬浇连续梁;刚构暂用 rigid_frame.py 内旧版)----
# 小项权重(合计 100%):跨中顶/底板各 10%、支点顶板 10%、支点附近底板 10%、
# 0 号段横梁底板 20%、腹板跨中/支点各 10%、翼缘端部 10%、纵向渐厚趋势 10%。
_D4_WEIGHTS: dict[str, float] = {
    "top_mid": 0.10, "bot_mid": 0.10, "top_root": 0.10, "bot_root": 0.10,
    "dia_root": 0.20, "web_mid": 0.10, "web_root": 0.10, "flange_tip": 0.10,
    "trend": 0.10,
}
_D4_ITEM_LABELS: dict[str, str] = {
    "top_mid": "跨中顶板厚", "bot_mid": "跨中底板厚", "top_root": "支点顶板厚",
    "bot_root": "支点附近底板厚", "dia_root": "横梁底板厚",
    "web_mid": "跨中腹板厚", "web_root": "支点腹板厚",
    "flange_tip": "翼缘端部厚", "trend": "纵向渐厚趋势",
}


def _d4_bot_root_deduction(r: float) -> float:
    """支点附近底板 T_root/H_root 比值 r 的扣分（取根部 0 号段单元底板厚）。

    宜 1/5~1/12。[1/12, 1/5] 自由;(1/5, 1/4] 扣 0~0.5 线性,>1/4 扣 1;
    [1/14, 1/12) 扣 0~0.5 线性,<1/14 扣 1。
    """
    eps = 1e-9
    if r > 1.0 / 4.0 + eps:
        return 1.0
    if r > 1.0 / 5.0 + eps:
        return _lerp(r, 1.0 / 5.0, 1.0 / 4.0, 0.0, 0.5)
    if r >= 1.0 / 12.0 - eps:
        return 0.0
    if r >= 1.0 / 14.0 - eps:
        return _lerp(r, 1.0 / 12.0, 1.0 / 14.0, 0.0, 0.5)
    return 1.0


def _d4_dia_root_deduction(r: float) -> float:
    """0 号梁段横梁底板 T_dia/H_root 比值 r 的扣分(横梁不单独建模,取根部单元底板厚)。

    宜 1/4~1/7。[1/7, 1/4] 自由;(1/4, 1/3.5] 扣 0~0.5 线性,>1/3.5 扣 1;
    [1/8, 1/7) 扣 0~0.5 线性,<1/8 扣 1。
    """
    eps = 1e-9
    if r > 1.0 / 3.5 + eps:
        return 1.0
    if r > 1.0 / 4.0 + eps:
        return _lerp(r, 1.0 / 4.0, 1.0 / 3.5, 0.0, 0.5)
    if r >= 1.0 / 7.0 - eps:
        return 0.0
    if r >= 1.0 / 8.0 - eps:
        return _lerp(r, 1.0 / 7.0, 1.0 / 8.0, 0.0, 0.5)
    return 1.0


def _score_md_d4(
    T_root: float | None,
    T_mid: float | None,
    H_root: float | None,
    thickness_profile: list[tuple[float, float]] | None = None,
    *,
    t_top_mid: float | None = None,
    t_top_root: float | None = None,
    t_dia_root: float | None = None,
    web_t_mid: float | None = None,
    web_t_support: float | None = None,
    flange_tip: float | None = None,
) -> tuple[float, dict[str, Any]]:
    """截面常规尺寸合理性(新准则,占比 20%;九小项各占 D4 的 10%~20%)。

    数据缺失的小项跳过,按剩余权重归一化;全部缺失 → 跳过给 1.0(同旧版)。
    「一侧腹板底板钢束>4束」难以从代码判定,T_mid≥0.22 无条件适用(常规 PC 箱梁均满足该前提)。
    纵向渐变安排在一个梁段内完成不扣分(准则明示),仅查跨中→支点单调渐厚。
    """
    items: dict[str, dict[str, Any]] = {}

    def _thresh(key: str, value: float | None, lo: float | None, hi: float | None, soft: float | None = None) -> None:
        """阈值型小项:越界扣 1(小项得分 0);value=None → 跳过。

        soft:越界软带宽度(m),在区间外 ±soft 内按线性扣分(0~1)。
        例:hi=1.20, soft=0.10 → 1.20~1.30 线性扣 0~1,>1.30 扣 1。
        """
        if value is None:
            items[key] = {"skipped": True, "note": "数据缺失,跳过"}
            return
        in_band = (lo is None or value >= lo - 1e-9) and (hi is None or value <= hi + 1e-9)
        if lo is not None and hi is not None:
            rng = f"[{lo}, {hi}]"
        elif lo is not None:
            rng = f">= {lo}"
        else:
            rng = f"<= {hi}"
        if in_band:
            ded = 0.0
        elif soft is not None:
            if hi is not None and value > hi + 1e-9 and value <= hi + soft + 1e-9:
                ded = (value - hi) / soft
            elif lo is not None and value < lo - 1e-9 and value >= lo - soft - 1e-9:
                ded = (lo - value) / soft
            else:
                ded = 1.0
        else:
            ded = 1.0
        score = max(0.0, 1.0 - ded)
        note = f"{value:.3f} m,要求 {rng}"
        if ded > 1e-9:
            note += f" → 扣 {ded:.2f}"
        items[key] = {"score": round(score, 4), "deduction": round(ded, 4), "note": note}

    _thresh("top_mid", t_top_mid, 0.22, None)
    _thresh("bot_mid", T_mid, 0.22, None)
    _thresh("top_root", t_top_root, 0.40, None)
    _thresh("web_mid", web_t_mid, 0.30, 0.60)
    _thresh("web_root", web_t_support, 0.60, 1.20)
    _thresh("flange_tip", flange_tip, 0.12, 0.25)

    # 支点附近底板:T_root/H_root 分段扣分
    if T_root is None or H_root is None or H_root <= 0:
        items["bot_root"] = {"skipped": True, "note": "T_root/H_root 缺失,跳过"}
    else:
        r = T_root / H_root
        ded = _d4_bot_root_deduction(r)
        items["bot_root"] = {
            "score": max(0.0, 1.0 - ded),
            "deduction": round(ded, 4),
            "note": f"T_root/H_root=1/{1.0 / r:.2f}(宜 1/5~1/12)" + ("" if ded <= 1e-9 else f" → 扣 {ded:.2f}"),
        }

    # 支点处横梁底板:t_dia_root 缺失时回退根部(0号段)单元底板厚 T_root
    t_dia = t_dia_root if t_dia_root is not None else T_root
    label_src = "=T_dia_root" if t_dia_root is not None else "=T_root"
    if t_dia is None or H_root is None or H_root <= 0:
        items["dia_root"] = {"skipped": True, "note": "T_root/H_root 缺失,跳过"}
    else:
        r = t_dia / H_root
        ded = _d4_dia_root_deduction(r)
        items["dia_root"] = {
            "score": max(0.0, 1.0 - ded),
            "deduction": round(ded, 4),
            "note": f"横梁底板厚({label_src})/H_root=1/{1.0 / r:.2f}(宜 1/4~1/7)" + ("" if ded <= 1e-9 else f" → 扣 {ded:.2f}"),
        }

    # 纵向渐厚趋势:顶/底/腹板自跨中向支点渐厚,不满足扣 1
    trend_parts: list[tuple[str, bool]] = []
    if thickness_profile:
        trend_parts.append(("底板", _is_thickness_trend_ok(thickness_profile)))
    if web_t_mid is not None and web_t_support is not None:
        trend_parts.append(("腹板", web_t_support >= web_t_mid - 1e-9))
    if t_top_mid is not None and t_top_root is not None:
        trend_parts.append(("顶板", t_top_root >= t_top_mid - 1e-9))
    if not trend_parts:
        items["trend"] = {"skipped": True, "note": "无纵向厚度数据,跳过"}
    else:
        bad = [name for name, ok in trend_parts if not ok]
        items["trend"] = {
            "score": 0.0 if bad else 1.0,
            "note": "向支点渐厚" if not bad else f"{'、'.join(bad)}未向支点渐厚 → 扣 1",
        }

    scored = [(k, float(it["score"])) for k, it in items.items() if "score" in it]
    if not scored:
        return 1.0, {"note": "无任何截面厚度数据,D4 跳过给 1.0", "items": items}
    w_sum = sum(_D4_WEIGHTS[k] for k, _ in scored)
    d4 = sum(_D4_WEIGHTS[k] * s for k, s in scored) / w_sum
    issues = [
        f"{_D4_ITEM_LABELS[k]}:{it['note']}"
        for k, it in items.items()
        if it.get("score", 1.0) < 1.0 - 1e-9
    ]
    return d4, {
        "items": items,
        "weights": dict(_D4_WEIGHTS),
        "level": _level_from_score(d4),
        "issue": "; ".join(issues) if issues else None,
        "issues": issues,
    }


# ---- D5 经济性与合理性(新准则,仅悬浇连续梁;刚构暂用 rigid_frame.py 内旧版)----
# 八小项固定权重(合计 100%;准则第一条「跨径/总长」拆为两项):跨径适配 10%、
# 全联总长 10%、截面最小梁高 10%、纵向钢束含筋量 20%、竖向预应力 20%、
# 边中跨比 10%、零号块长度 10%、主梁材料 10%。
_D5_WEIGHTS: dict[str, float] = {
    "span_fit": 0.10, "total_length": 0.10, "min_height": 0.10,
    "steel_ratio": 0.20, "vertical_pst": 0.20, "side_mid_ratio": 0.10,
    "zero_block": 0.10, "material": 0.10,
}
_D5_ITEM_LABELS: dict[str, str] = {
    "span_fit": "跨径适配性", "total_length": "全联总长", "min_height": "截面最小梁高",
    "steel_ratio": "纵向钢束含筋量", "vertical_pst": "竖向预应力",
    "side_mid_ratio": "边中跨比", "zero_block": "零号块长度", "material": "主梁材料",
}


def _d5_span_fit_deduction(L: float) -> float:
    """跨径适配:[50,160] 自由;[40,50)&(160,170] 扣 0~0.25 线性;(170,200] 扣 0.5;其余扣 1。"""
    eps = 1e-9
    if L < 40.0 - eps or L > 200.0 + eps:
        return 1.0
    if 50.0 - eps <= L <= 160.0 + eps:
        return 0.0
    if L < 50.0 - eps:
        return _lerp(L, 50.0, 40.0, 0.0, 0.25)
    if L <= 170.0 + eps:
        return _lerp(L, 160.0, 170.0, 0.0, 0.25)
    return 0.5


def _d5_min_height_deduction(h: float) -> float:
    """所有截面梁高 ≥2.2 不扣;[2.0,2.2) 扣 0.1;[1.8,2.0) 扣 0.5;<1.8 扣 1。"""
    eps = 1e-9
    if h >= 2.2 - eps:
        return 0.0
    if h >= 2.0 - eps:
        return 0.1
    if h >= 1.8 - eps:
        return 0.5
    return 1.0


def _d5_steel_ratio_limit(L: float | None) -> float | None:
    """含筋量上限(kg/m³):[50,70)→50;[70,100)→60;[100,150)→90;[150,200]→130;其余不评上限。"""
    if L is None:
        return None
    eps = 1e-9
    if 50.0 - eps <= L < 70.0 - eps:
        return 50.0
    if 70.0 - eps <= L < 100.0 - eps:
        return 60.0
    if 100.0 - eps <= L < 150.0 - eps:
        return 90.0
    if 150.0 - eps <= L <= 200.0 + eps:
        return 130.0
    return None


def _d5_steel_ratio_deduction(value: float, limit: float) -> float:
    """含筋量超上限后 10 kg/m³ 内从 0 到 1 线性扣分，超过该区间扣满 1 分。"""
    return max(0.0, min(1.0, (value - limit) / 10.0))


def _d5_side_mid_deduction(r: float) -> float:
    """边中跨比 r 的扣分:[0.62,0.75] 自由;[0.55,0.62)&(0.75,0.82] 扣 0.1;
    [0.5,0.55)&(0.82,0.88] 扣 0.1~0.6 线性;[0.47,0.5)&(0.88,0.92] 扣 0.7;其余扣 1。"""
    eps = 1e-9
    if 0.62 - eps <= r <= 0.75 + eps:
        return 0.0
    if 0.55 - eps <= r < 0.62 - eps:
        return 0.1
    if 0.75 + eps < r <= 0.82 + eps:
        return 0.1
    if 0.5 - eps <= r < 0.55 - eps:
        return _lerp(r, 0.55, 0.5, 0.1, 0.6)
    if 0.82 + eps < r <= 0.88 + eps:
        return _lerp(r, 0.82, 0.88, 0.1, 0.6)
    if 0.47 - eps <= r < 0.5 - eps:
        return 0.7
    if 0.88 + eps < r <= 0.92 + eps:
        return 0.7
    return 1.0


def _d5_zero_block_deduction(L0: float) -> float:
    """零号块长度:[9,14] 自由;(14,20] 扣 0~0.4 线性;(20,25] 扣 0.4~0.9 线性;
    [8,9) 扣 0.5;<8 或 >25 扣 1。"""
    eps = 1e-9
    if 9.0 - eps <= L0 <= 14.0 + eps:
        return 0.0
    if 14.0 + eps < L0 <= 20.0 + eps:
        return _lerp(L0, 14.0, 20.0, 0.0, 0.4)
    if 20.0 + eps < L0 <= 25.0 + eps:
        return _lerp(L0, 20.0, 25.0, 0.4, 0.9)
    if 8.0 - eps <= L0 < 9.0 - eps:
        return 0.5
    return 1.0


def _d5_material_requirement(L: float) -> int | None:
    """材料最低等级:[60,120) → C55;[120,170] → C60;其余跨径不做评判(返回 None)。"""
    eps = 1e-9
    if 60.0 - eps <= L < 120.0 - eps:
        return 55
    if 120.0 - eps <= L <= 170.0 + eps:
        return 60
    return None


def _score_md_d5(
    L: float | None,
    H_mid: float | None,
    total_length: float | None,
    has_vertical_tendon: bool,
    pst_steel_ratio: float | None = None,
    span_lengths: list[float] | None = None,
    zero_block_len: float | None = None,
    concrete_grade: int | None = None,
) -> tuple[float, dict[str, Any]]:
    """经济性与合理性(新准则,占比 30%;八小项各占 D5 的 10%~20%)。

    数据缺失的小项跳过,按剩余权重归一化;全部缺失 → 跳过给 1.0。
    竖向预应力判定沿用 _has_vertical_tendon(腹板竖筋 WEBVERTICALREBAR 落支点两侧 L/3,
    或竖向 PST),剪力较大范围为支点两侧 L/4、检查范围 L/3,与准则一致。
    """
    items: dict[str, dict[str, Any]] = {}

    def _put(key: str, ded: float | None, note: str) -> None:
        if ded is None:
            items[key] = {"skipped": True, "note": note}
            return
        items[key] = {
            "score": max(0.0, 1.0 - ded),
            "deduction": round(ded, 4),
            "note": note + ("" if ded <= 1e-9 else f" → 扣 {ded:.2f}"),
        }

    # 1) 跨径适配
    if L is None:
        _put("span_fit", None, "L 缺失,跳过")
    else:
        _put("span_fit", _d5_span_fit_deduction(L), f"L={L:g} m(适配区间 50~160 m)")

    # 2) 全联总长 >1000m 扣 1(联长过长温度效应巨大,经济性差)
    if total_length is None:
        _put("total_length", None, "全联总长缺失,跳过")
    else:
        _put("total_length", 1.0 if total_length > 1000.0 + 1e-9 else 0.0,
             f"全联总长={total_length:.1f} m(限 1000 m)")

    # 3) 截面最小梁高(所有截面 >2.2m;工人箱内作业效率)
    if H_mid is None:
        _put("min_height", None, "最小梁高缺失,跳过")
    else:
        _put("min_height", _d5_min_height_deduction(H_mid), f"最小梁高={H_mid:g} m(宜 ≥2.2 m)")

    # 4) 纵向钢束含筋量(有效预应力):<35 扣 1;超上限后 10 kg/m³ 内线性扣 0~1
    if pst_steel_ratio is None:
        _put("steel_ratio", None, "含筋量缺失(无 PST 或截面面积),跳过")
    else:
        limit = _d5_steel_ratio_limit(L)
        if pst_steel_ratio < 35.0 - 1e-9:
            ded, why = 1.0, "< 35 kg/m³ 下限"
        elif limit is not None and pst_steel_ratio > limit + 1e-9:
            ded = _d5_steel_ratio_deduction(pst_steel_ratio, limit)
            why = f"> {limit:g} kg/m³ 上限({limit:g}~{limit + 10:g} 线性扣分)"
        else:
            ded, why = 0.0, ""
        lim_s = f",上限 {limit:g}" if limit is not None else ""
        _put("steel_ratio", ded, f"{pst_steel_ratio:.1f} kg/m³(下限 35{lim_s})" + (f",{why}" if why else ""))

    # 5) 竖向预应力:L>75m 不设置扣 1
    if L is None:
        _put("vertical_pst", None, "L 缺失,跳过")
    elif L <= 75.0 + 1e-9:
        _put("vertical_pst", 0.0, f"L={L:g} m ≤ 75 m,不作要求")
    else:
        _put("vertical_pst", 0.0 if has_vertical_tendon else 1.0,
             "已设竖向预应力(腹板竖筋/竖向 PST)" if has_vertical_tendon else "L>75 m 未设竖向预应力")

    # 6) 边中跨比(三跨布置,取左/右边跨最不利)
    if not span_lengths or len(span_lengths) < 3:
        _put("side_mid_ratio", None, "跨径序列缺失或非三跨布置,跳过")
    else:
        mid = max(span_lengths)
        ratios = (span_lengths[0] / mid, span_lengths[-1] / mid)
        deds = [_d5_side_mid_deduction(r) for r in ratios]
        worst = max(deds)
        _put("side_mid_ratio", worst,
             f"边中跨比 {ratios[0]:.3f} / {ratios[1]:.3f}(宜 0.62~0.75,取最不利)")

    # 7) 零号块长度
    if zero_block_len is None:
        _put("zero_block", None, "零号块长度缺失(无 0号块 单元组或节点几何),跳过")
    else:
        _put("zero_block", _d5_zero_block_deduction(zero_block_len),
             f"零号块长度={zero_block_len:g} m(宜 9~14 m)")

    # 8) 主梁材料:[60,120) 需 C55+;[120,170] 需 C60+;其余跨径不评判
    req = _d5_material_requirement(L) if L is not None else None
    if req is None:
        _put("material", None, "跨径不在评判区间(60~170 m)或 L 缺失,跳过")
    elif concrete_grade is None:
        _put("material", None, "混凝土等级缺失,跳过")
    else:
        _put("material", 0.0 if concrete_grade >= req else 1.0,
             f"C{concrete_grade}(L={L:g} m 要求 ≥C{req})")

    scored = [(k, float(it["score"])) for k, it in items.items() if "score" in it]
    if not scored:
        return 1.0, {"note": "无经济数据,D5 跳过给 1.0", "items": items}
    w_sum = sum(_D5_WEIGHTS[k] for k, _ in scored)
    d5 = sum(_D5_WEIGHTS[k] * s for k, s in scored) / w_sum
    issues = [
        f"{_D5_ITEM_LABELS[k]}:{it['note']}"
        for k, it in items.items()
        if it.get("score", 1.0) < 1.0 - 1e-9
    ]
    return d5, {
        "items": items,
        "weights": dict(_D5_WEIGHTS),
        "level": _level_from_score(d5),
        "issue": "; ".join(issues) if issues else None,
        "issues": issues,
    }


# MD 五维权重(测试方确认,总分 1 分制)
_MD_WEIGHTS: dict[str, float] = {
    "D1_H_root": 0.20,
    "D2_H_mid": 0.15,
    "D3_n_H": 0.15,
    "D4_thickness": 0.20,
    "D5_consistency": 0.30,
}


def score_variable_section(params: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """悬浇连续梁 / 变截面连续箱梁:MD 5 维。

    L = params['L'](设计主跨,ground truth,由调用方注入)。
    """
    L = params["L"]
    # 各 D 函数自行判 L 三态(缺失 / 超出适用范围 / 有效):
    # D1 按分跨高跨比表取档(50 以下用 50 档,170 以上用 170 档);
    # D2/D3/D5 超 50-200m 范围仍判 0 分(与旧 L_valid 折叠等价),仅文案区分,不改判分。
    d1, d1d = _score_md_d1(L, params["H_root"])
    d2, d2d = _score_md_d2(L, params["H_mid"])
    d3, d3d = _score_md_d3(L, params.get("height_profile"))
    d4, d4d = _score_md_d4(
        params["T_root"],
        params["T_mid"],
        params["H_root"],
        params.get("thickness_profile"),
        t_top_mid=params.get("T_top_mid"),
        t_top_root=params.get("T_top_root"),
        t_dia_root=params.get("T_dia_root"),
        web_t_mid=params.get("web_t_mid"),
        web_t_support=params.get("web_t_support"),
        flange_tip=params.get("flange_tip"),
    )
    d5, d5d = _score_md_d5(
        L,
        params["H_mid"],
        params.get("total_length"),
        params.get("has_vertical_tendon", False),
        pst_steel_ratio=params.get("pst_steel_ratio"),
        span_lengths=params.get("span_lengths"),
        zero_block_len=params.get("zero_block_len"),
        concrete_grade=params.get("concrete_grade"),
    )
    return _assemble(params, [
        ("D1_H_root", d1, d1d), ("D2_H_mid", d2, d2d), ("D3_n_H", d3, d3d),
        ("D4_thickness", d4, d4d), ("D5_consistency", d5, d5d),
    ], weights=_MD_WEIGHTS)
