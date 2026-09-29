"""Rigid frame bridge geometry extraction and scoring (MD D6)."""
from __future__ import annotations

import ast
import re
from typing import Any

from .cantilever import (
    _D1_TOL1,
    _D1_TOL2,
    _D1_TOL3,
    _D2_TOL1,
    _D2_TOL2,
    _D2_TOL3,
    _D4_ITEM_LABELS,
    _d5_min_height_deduction,
    _d5_steel_ratio_deduction,
    _d5_zero_block_deduction,
    _fit_height_exponent,
)
from ..common import _assemble, _const_value, _lerp, _level_from_score

_ELEM_ID_RANGE = re.compile(r"^(\d+)\s*to\s*(\d+)$", re.IGNORECASE)


def _expand_elem_id_token(tok: Any) -> list[int]:
    """展开单元编号标记:数字或 '107to158' → [107,...,158]。"""
    if isinstance(tok, bool):
        return []
    if isinstance(tok, int):
        return [tok]
    if isinstance(tok, float) and tok.is_integer():
        return [int(tok)]
    if isinstance(tok, str):
        m = _ELEM_ID_RANGE.match(tok.strip())
        if not m:
            return []
        a, b = int(m.group(1)), int(m.group(2))
        lo, hi = (a, b) if a <= b else (b, a)
        return list(range(lo, hi + 1))
    return []


def _scan_element_groups(tree: ast.AST | None) -> dict[str, set[int]]:
    """从 _6_element.py 解析 engine.element.group.create(name, op, *refs)。

    返回 {组名: 单元编号集合}。支持 op:
      - "c": 创建(可空);若带 refs 则一并加入
      - "a" / "s": 添加/替换为给定编号
      - "r": 从组中移除
      - "ra": 清空组
    """
    if tree is None:
        return {}
    groups: dict[str, set[int]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "create":
            continue
        # engine.element.group.create(...)
        if not isinstance(func.value, ast.Attribute) or func.value.attr != "group":
            continue
        base = ast.unparse(func.value.value) if hasattr(ast, "unparse") else None
        if base != "engine.element":
            continue
        args = node.args
        if len(args) < 2:
            continue
        name = _const_value(args[0])
        op = _const_value(args[1])
        if not isinstance(name, str) or not isinstance(op, str):
            continue
        refs: list[int] = []
        for a in args[2:]:
            refs.extend(_expand_elem_id_token(_const_value(a)))
        op_l = op.lower()
        if op_l == "c":
            groups.setdefault(name, set()).update(refs)
        elif op_l in ("a", "s"):
            groups.setdefault(name, set()).update(refs)
        elif op_l == "r":
            if name in groups:
                groups[name].difference_update(refs)
        elif op_l == "ra":
            groups[name] = set()
    return groups


def _is_pier_section(sec: dict[str, Any]) -> bool:
    """墩截面:类型 RECT,或名为「桥墩」。"""
    t = (sec.get("type") or "").upper()
    if t == "RECT":
        return True
    return (sec.get("name") or "") == "桥墩"


def _pier_element_nos(
    groups: dict[str, set[int]],
    beams: list[dict[str, Any]],
    sections: list[dict[str, Any]],
) -> tuple[set[int], str | None]:
    """优先单元组名含「桥墩」,否则挂 RECT/桥墩截面的 BEAM3D。

    返回 (单元编号集合, 来源标签)。
    """
    group_nos: set[int] = set()
    for name, elems in groups.items():
        if "桥墩" in name:
            group_nos |= elems
    if group_nos:
        return group_nos, "element_group"

    pier_sec_nos = {
        s["no"] for s in sections
        if s.get("no") is not None and _is_pier_section(s)
    }
    if not pier_sec_nos:
        return set(), None
    rect_nos = {
        b["no"] for b in beams
        if b["nSec1"] in pier_sec_nos or b["nSec2"] in pier_sec_nos
    }
    if rect_nos:
        return rect_nos, "rect_section"
    return set(), None


def _coords_from_element_nos(
    elem_nos: set[int],
    beams: list[dict[str, Any]],
    nodes: dict[int, tuple[float, float, float]],
) -> list[tuple[float, float, float]]:
    """单元编号 → 端点节点坐标(去重)。"""
    beam_by_no = {b["no"]: b for b in beams}
    out: list[tuple[float, float, float]] = []
    seen: set[int] = set()
    for eno in elem_nos:
        b = beam_by_no.get(eno)
        if b is None:
            continue
        for nid in (b["node1"], b["node2"]):
            if nid in seen:
                continue
            coord = nodes.get(nid)
            if coord is None:
                continue
            seen.add(nid)
            out.append(coord)
    return out


def _geometry_from_pier_and_beam_nodes(
    pier_nodes: list[tuple[float, float, float]],
    beam_nodes: list[tuple[float, float, float]],
) -> dict[str, Any] | None:
    """对墩节点按 x 聚类,算边跨/主跨/墩高。失败返回 None。"""
    if not pier_nodes or len(beam_nodes) < 2:
        return None

    pier_xs = sorted({x for x, _, _ in pier_nodes})
    clusters: list[list[float]] = []
    for x in pier_xs:
        if not clusters or x - clusters[-1][0] > 25.0:
            clusters.append([x])
        else:
            clusters[-1].append(x)

    true_pier_centers: list[float] = []
    for cluster in clusters:
        cx = sum(cluster) / len(cluster)
        col_nodes = [(x, y, z) for x, y, z in pier_nodes if abs(x - cx) <= 25.0]
        if col_nodes:
            z_range = max(z for _, _, z in col_nodes) - min(z for _, _, z in col_nodes)
            if z_range > 5.0:
                true_pier_centers.append(cx)

    if not true_pier_centers:
        return None

    true_pier_centers.sort()
    pier_heights: list[float] = []
    for cx in true_pier_centers:
        col_nodes = [(x, y, z) for x, y, z in pier_nodes if abs(x - cx) <= 25.0]
        if col_nodes:
            pier_heights.append(
                max(z for _, _, z in col_nodes) - min(z for _, _, z in col_nodes)
            )

    # 单墩(T 形刚构)无墩间距主跨,main_span/side_spans 置 None,由调用方回退 L
    if len(true_pier_centers) < 2 or not beam_nodes:
        return {
            "side_spans": None,
            "main_span": None,
            "pier_heights": pier_heights,
        }

    beam_xs = sorted({x for x, _, _ in beam_nodes})
    left_abutment = beam_xs[0]
    right_abutment = beam_xs[-1]
    return {
        "side_spans": (
            true_pier_centers[0] - left_abutment,
            right_abutment - true_pier_centers[-1],
        ),
        "main_span": true_pier_centers[-1] - true_pier_centers[0],
        "pier_heights": pier_heights,
    }


def _extract_rigid_frame_geometry(
    nodes: dict[int, tuple[float, float, float]],
    sections: list[dict[str, Any]] | None = None,
    beams: list[dict[str, Any]] | None = None,
    elem_tree: ast.AST | None = None,
) -> dict[str, Any]:
    """提取连续刚构跨径布置与墩高。

    墩节点识别优先级:
      1. 单元组名含「桥墩」(如「桥墩单元组」) → 组内单元端点
      2. 截面为 RECT / 名「桥墩」的 BEAM3D 端点
      3. 坐标启发式:z < -0.5 或 |y| > 0.5(兼容旧模板)

    主梁端点仍用 |y|≤0.5 且 |z|≤0.5 估计桥台位置。
    墩按 x 聚类(容差 25m,合并双肢),z 跨度 > 5m 才认作真墩。
    """
    empty = {
        "side_spans": None,
        "main_span": None,
        "pier_heights": None,
        "pier_source": None,
    }
    if not nodes:
        return empty

    beam_nodes = [
        (x, y, z) for x, y, z in nodes.values()
        if abs(y) <= 0.5 and abs(z) <= 0.5
    ]

    pier_nodes: list[tuple[float, float, float]] = []
    pier_source: str | None = None

    if beams is not None and sections is not None:
        groups = _scan_element_groups(elem_tree)
        pier_enos, src = _pier_element_nos(groups, beams, sections)
        if pier_enos:
            pier_nodes = _coords_from_element_nos(pier_enos, beams, nodes)
            if pier_nodes:
                pier_source = src

    if not pier_nodes:
        pier_nodes = [
            (x, y, z) for x, y, z in nodes.values()
            if z < -0.5 or abs(y) > 0.5
        ]
        if pier_nodes:
            pier_source = "coord_heuristic"

    geo = _geometry_from_pier_and_beam_nodes(pier_nodes, beam_nodes)
    if geo is None:
        return empty
    geo["pier_source"] = pier_source
    return geo
# ---- D1 支点梁高(刚构准则:80~250m 分跨高跨比表 + 三段误差限扣分,占比 20%)----
# 非 UHPC 前提下主跨宜 ≤200m;200~250m 为极限区间(支点高超 12m 挂篮难控);
# 常规适用下限约 80m(挂篮施工经济性)。非表列跨径向下取档(如 100~110m 取 100m);
# 80m 以下用 80m 档,250m 以上用 250m 档。
# (标准跨径 m, 区间下限分母 lo_den, 区间上限分母 hi_den)
# 允许高跨比区间 = [1/lo_den, 1/hi_den];准则原文写作「1/hi_den~1/lo_den」
_D1_RATIO_TABLE_RIGID: tuple[tuple[float, float, float], ...] = (
    (80.0, 16.7, 15.09),    # h 4.8~5.3
    (90.0, 17.0, 15.5),     # h 5.3~5.8
    (100.0, 17.25, 15.7),   # h 5.8~6.4
    (110.0, 17.2, 15.72),   # h 6.5~7
    (120.0, 17.2, 15.4),    # h 7~7.8
    (130.0, 17.5, 15.8),    # h 7.5~8.2
    (140.0, 17.5, 15.5),    # h 8~9
    (150.0, 17.0, 15.78),   # h 8.8~9.5;原文「1/15.78/17」按 1/15.78~1/17
    (160.0, 17.1, 16.0),    # h 9.4~10
    (170.0, 17.71, 16.19),  # h 9.6~10.5
    (180.0, 18.0, 16.66),   # h 10~10.8
    (190.0, 18.1, 16.66),   # h 10.5~11.4
    (200.0, 19.1, 16.9),    # h 10.5~11.8
    (210.0, 19.1, 16.8),    # h 11~12.5
    (220.0, 19.2, 16.9),    # h 11.5~13
    (230.0, 19.3, 17.0),    # h 11.9~13.5
    (240.0, 19.6, 17.14),   # h 12.2~14
    (250.0, 20.0, 17.48),   # h 12.5~14.3
)


def _d1_ratio_band_rigid(L: float) -> tuple[float, float, float, float, float]:
    """按 L 查刚构高跨比允许区间。返回 (lo, hi, 标准跨径档, lo_den, hi_den)。

    非表列跨径向下取最近标准跨径档(如 100~110m 取 100m 档);
    80m 以下用 80m 档,250m 以上用 250m 档。
    """
    row = _D1_RATIO_TABLE_RIGID[0]
    for r in _D1_RATIO_TABLE_RIGID:
        if L >= r[0]:
            row = r
        else:
            break
    std, lo_den, hi_den = row
    return 1.0 / lo_den, 1.0 / hi_den, std, lo_den, hi_den


def _score_md_d1(L: float | None, H_root: float | None) -> tuple[float, dict[str, Any]]:
    """支点(根部)梁高 H_root 评分(刚构准则:分跨高跨比区间,占比 20%)。

    规则与悬浇连续梁 D1 同构(三段误差限 1/1500、1/500、1/100 线性扣分),
    但查刚构专属 80~250m 高跨比表:
      - r = H_root/L 在区间内:不扣分
      - 偏差 d(高跨比绝对差):0<d<=1/1500 扣 0→0.2;1/1500<d<=1/500 扣 0.2→0.8;
        1/500<d<=1/100 扣 0.8→1;d>1/100 扣 1
    背景:非 UHPC 前提下主跨限 200m 以内,200~250m 为极限区间(支点高超 12m
    挂篮风阻与悬臂自重难控);常规适用下限约 80m(挂篮施工经济性)。
    """
    if L is None:
        return 0.0, {"issue": "L 缺失,无法核对根部梁高"}
    if L <= 0:
        return 0.0, {"issue": f"L={L} 非法,无法核对根部梁高"}
    if H_root is None:
        return 0.0, {"issue": "H_root 缺失"}

    lo, hi, std, lo_den, hi_den = _d1_ratio_band_rigid(L)
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


# ---- D2 跨中梁高(刚构准则:80~250m 分跨高跨比表 + 三段误差限扣分,占比 15%)----
# 墩身约束减轻跨中正弯矩,刚构跨中比连续梁更轻薄;>150m 自重主导、高跨比扁平化;
# L>200m 跨中高跨比逼近 1/55~1/56。非表列跨径向下取档(如 130~140m 取 130m);
# 80m 以下用 80m 档,250m 以上用 250m 档。第一档误差限为 1/1000(非 D1 的 1/1500)。
# (标准跨径 m, 区间下限分母 lo_den, 区间上限分母 hi_den)
# 允许高跨比区间 = [1/lo_den, 1/hi_den];准则原文写作「1/hi_den~1/lo_den」
_D2_RATIO_TABLE_RIGID: tuple[tuple[float, float, float], ...] = (
    (80.0, 40.0, 34.78),    # h 2~2.3
    (90.0, 40.9, 37.5),     # h 2.2~2.4
    (100.0, 45.5, 37.0),    # h 2.2~2.7
    (110.0, 45.9, 37.93),   # h 2.4~2.9
    (120.0, 48.0, 37.5),    # h 2.5~3.2
    (130.0, 46.5, 38.2),    # h 2.8~3.4
    (140.0, 46.67, 36.8),   # h 3~3.8
    (150.0, 45.5, 36.5),    # h 3.3~4.1
    (160.0, 45.72, 36.3),   # h 3.5~4.4
    (170.0, 44.74, 36.17),  # h 3.8~4.7
    (180.0, 45.0, 36.0),    # h 4~5
    (190.0, 46.35, 35.8),   # h 4.1~5.3
    (200.0, 47.62, 36.36),  # h 4.2~5.5
    (210.0, 50.0, 37.5),    # h 4.2~5.6
    (220.0, 51.2, 38.59),   # h 4.3~5.7
    (230.0, 53.5, 39.65),   # h 4.3~5.8
    (240.0, 54.55, 40.67),  # h 4.4~5.9
    (250.0, 55.6, 41.66),   # h 4.5~6
)


def _d2_ratio_band_rigid(L: float) -> tuple[float, float, float, float, float]:
    """按 L 查刚构跨中高跨比允许区间。返回 (lo, hi, 标准跨径档, lo_den, hi_den)。

    非表列跨径向下取最近标准跨径档(如 130~140m 取 130m 档);
    80m 以下用 80m 档,250m 以上用 250m 档。
    """
    row = _D2_RATIO_TABLE_RIGID[0]
    for r in _D2_RATIO_TABLE_RIGID:
        if L >= r[0]:
            row = r
        else:
            break
    std, lo_den, hi_den = row
    return 1.0 / lo_den, 1.0 / hi_den, std, lo_den, hi_den


def _score_md_d2(L: float | None, H_mid: float | None) -> tuple[float, dict[str, Any]]:
    """跨中梁高 H_mid 评分(刚构准则:分跨高跨比区间,占比 15%)。

    规则与悬浇连续梁 D2 同构(三段误差限 1/1000、1/500、1/100 线性扣分),
    但查刚构专属 80~250m 表;刚构无连续梁「70m 以下 H∈[1.8,2) 只扣 0.5」特例。
    背景:墩身约束减轻跨中正弯矩,刚构跨中比连续梁更轻薄;跨径>150m 后自重主导,
    高跨比扁平化,L>200m 跨中高跨比逼近 1/55~1/56;跨中梁高受箱内施工最小净空
    (≮1.8~2.0m) 底线约束。
    """
    if L is None:
        return 0.0, {"issue": "L 缺失,无法核对跨中梁高"}
    if L <= 0:
        return 0.0, {"issue": f"L={L} 非法,无法核对跨中梁高"}
    if H_mid is None:
        return 0.0, {"issue": "H_mid 缺失"}

    lo, hi, std, lo_den, hi_den = _d2_ratio_band_rigid(L)
    r = H_mid / L
    band_str = f"1/{hi_den:g} ~ 1/{lo_den:g}"
    ratio_str = f"1/{L / H_mid:.2f}" if H_mid > 0 else "∞"

    if r < lo:
        d = lo - r
    elif r > hi:
        d = r - hi
    else:
        d = 0.0

    if d <= 0.0:
        deduction = 0.0
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
    if deduction > 1e-9:
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


def _d3_deduction_rigid(L: float, n: float) -> tuple[float, str, float | None]:
    """按 L 分档 + 幂次 n 给扣分(刚构,占比 15%)。返回 (扣分, 档标签, 优值或 None)。

    悬浇段梁高变化曲线。70~100m 首选 1.8 次(备选 2.0);100m+ 首选 1.5~1.7 次(备选 1.8)。
    分档(评分以字母档为准;B/C 规则相同):
      A. [50,70)(L<50 同档):n ∈ [1,3] 不扣,否则扣 1
      B. [70,100]:优选 2(1.8 不扣);[1.5,1.6)&(2,3] 扣 0.5;(-∞,1.5)&(3,+∞) 扣 1
      C. (100,120):同 B
      D. [120,150]:优选 1.8(2 不扣);[1.4,1.5)&(2,3] 扣 0.5;(-∞,1.4)&(3,+∞) 扣 1
      D. (150,200]:优选 1.5;[1.4,1.5)&(1.8,2] 扣 0.5;(-∞,1.4)&(2,+∞) 扣 1
      E. (200,250]:优选 1.5;[1.4,1.5)&(1.7,1.8] 扣 0.1;(1.8,2] 扣 0.25;(-∞,1.4)&(2,+∞) 扣 1
      F. (250,+∞]:任意幂次扣 1
    """
    eps = 1e-9
    if L > 250.0:
        return 1.0, "F((250,+∞])", None
    if L < 70.0:  # A 档(L<50 同按「跨度太小」处理)
        if 1.0 - eps <= n <= 3.0 + eps:
            return 0.0, "A([50,70))", None
        return 1.0, "A([50,70))", None
    if L < 120.0:  # B [70,100] / C (100,120),规则相同
        band = "B([70,100])" if L <= 100.0 else "C((100,120))"
        if n < 1.5 - eps or n > 3.0 + eps:
            return 1.0, band, 2.0
        if (1.5 - eps <= n < 1.6 - eps) or (2.0 + eps < n <= 3.0 + eps):
            return 0.5, band, 2.0
        return 0.0, band, 2.0
    if L <= 150.0:  # D 档 [120,150]
        if n < 1.4 - eps or n > 3.0 + eps:
            return 1.0, "D([120,150])", 1.8
        if (1.4 - eps <= n < 1.5 - eps) or (2.0 + eps < n <= 3.0 + eps):
            return 0.5, "D([120,150])", 1.8
        return 0.0, "D([120,150])", 1.8
    if L <= 200.0:  # D 档 (150,200]
        if n < 1.4 - eps or n > 2.0 + eps:
            return 1.0, "D((150,200])", 1.5
        if (1.4 - eps <= n < 1.5 - eps) or (1.8 + eps < n <= 2.0 + eps):
            return 0.5, "D((150,200])", 1.5
        return 0.0, "D((150,200])", 1.5
    # E 档 (200,250]
    if n < 1.4 - eps or n > 2.0 + eps:
        return 1.0, "E((200,250])", 1.5
    if (1.4 - eps <= n < 1.5 - eps) or (1.7 + eps < n <= 1.8 + eps):
        return 0.1, "E((200,250])", 1.5
    if 1.8 + eps < n <= 2.0 + eps:
        return 0.25, "E((200,250])", 1.5
    return 0.0, "E((200,250])", 1.5


def _score_md_d3(
    L: float | None,
    height_profile: list[tuple[float, float]] | None = None,
) -> tuple[float, dict[str, Any]]:
    """n_H:悬浇段梁高变化曲线幂次评分(刚构分跨分档扣分,占比 15%)。

    适用对象:悬浇连续刚构;连续梁走 cantilever.py。
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

    deduction, band, preferred = _d3_deduction_rigid(L, n_H)
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


def _d4_bot_root_deduction_rigid(r: float) -> float:
    """刚构支点附近底板 T_root/H_root 比值 r 的扣分（取根部 0 号段单元底板厚）。

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


# 小项权重(合计 100%):跨中顶/底板各 10%、支点顶板 10%、支点附近底板 10%、
# 0 号段横梁底板 20%、腹板跨中/支点各 10%、翼缘端部 10%、纵向渐厚趋势 10%。
_D4_WEIGHTS_RIGID: dict[str, float] = {
    "top_mid": 0.10, "bot_mid": 0.10, "top_root": 0.10, "bot_root": 0.10,
    "dia_root": 0.20, "web_mid": 0.10, "web_root": 0.10, "flange_tip": 0.10,
    "trend": 0.10,
}


def _d4_dia_root_deduction_rigid(r: float) -> float:
    """刚构 0 号梁段横梁底板 T_dia/H_root 比值 r 的扣分。

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
    """截面常规尺寸合理性(刚构准则,占比 20%;九小项各占 D4 的 10%~20%)。

    与悬浇连续梁 D4 同构(缺项跳过按剩余权重归一化,全缺给 1.0),差异:
      - 跨中腹板:刚构 30~65cm(梁 30~60cm)
    支点附近底板宜 1/5~1/12,0 号段横梁底板宜 1/4~1/7;腹板 1:12 坡度不扣分。
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
    _thresh("web_mid", web_t_mid, 0.30, 0.65)
    _thresh("web_root", web_t_support, 0.60, 1.20)
    _thresh("flange_tip", flange_tip, 0.12, 0.25)

    # 支点附近底板:T_root/H_root 分段扣分(刚构档)
    if T_root is None or H_root is None or H_root <= 0:
        items["bot_root"] = {"skipped": True, "note": "T_root/H_root 缺失,跳过"}
    else:
        r = T_root / H_root
        ded = _d4_bot_root_deduction_rigid(r)
        items["bot_root"] = {
            "score": max(0.0, 1.0 - ded),
            "deduction": round(ded, 4),
            "note": f"T_root/H_root=1/{1.0 / r:.2f}(宜 1/5~1/12)" + ("" if ded <= 1e-9 else f" → 扣 {ded:.2f}"),
        }

    # 支点处横梁底板:t_dia_root 缺失时回退根部(0号段)单元底板厚 T_root(同连续梁)
    t_dia = t_dia_root if t_dia_root is not None else T_root
    label_src = "=T_dia_root" if t_dia_root is not None else "=T_root"
    if t_dia is None or H_root is None or H_root <= 0:
        items["dia_root"] = {"skipped": True, "note": "T_root/H_root 缺失,跳过"}
    else:
        r = t_dia / H_root
        ded = _d4_dia_root_deduction_rigid(r)
        items["dia_root"] = {
            "score": max(0.0, 1.0 - ded),
            "deduction": round(ded, 4),
            "note": f"横梁底板厚({label_src})/H_root=1/{1.0 / r:.2f}(宜 1/4~1/7)" + ("" if ded <= 1e-9 else f" → 扣 {ded:.2f}"),
        }

    # 纵向渐厚趋势:顶/底/腹板自跨中向支点渐厚,不满足扣 1(同连续梁)
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
    w_sum = sum(_D4_WEIGHTS_RIGID[k] for k, _ in scored)
    d4 = sum(_D4_WEIGHTS_RIGID[k] * s for k, s in scored) / w_sum
    issues = [
        f"{_D4_ITEM_LABELS[k]}:{it['note']}"
        for k, it in items.items()
        if it.get("score", 1.0) < 1.0 - 1e-9
    ]
    return d4, {
        "items": items,
        "weights": dict(_D4_WEIGHTS_RIGID),
        "level": _level_from_score(d4),
        "issue": "; ".join(issues) if issues else None,
        "issues": issues,
    }


# ---- D5 经济性与合理性(刚构准则,占比 30%;九小项各占 D5 的 10%~20%)----
# 小项权重(测试方确认,合计 100%):跨径适配 10%、全联总长 10%、截面最小梁高 10%、
# 纵向钢束含筋量 20%、竖向预应力 10%、边中跨比 10%、墩身高度 10%、零号块长度 10%、
# 主梁材料 10%。刚构无 D6:原 D6 的边中跨比/墩高并入 D5 第六、七条。
_D5_WEIGHTS_RIGID: dict[str, float] = {
    "span_fit": 0.10, "total_length": 0.10, "min_height": 0.10,
    "steel_ratio": 0.20, "vertical_pst": 0.10, "side_mid_ratio": 0.10,
    "pier_height": 0.10, "zero_block": 0.10, "material": 0.10,
}
_D5_ITEM_LABELS_RIGID: dict[str, str] = {
    "span_fit": "跨径适配性", "total_length": "全联总长", "min_height": "截面最小梁高",
    "steel_ratio": "纵向钢束含筋量", "vertical_pst": "竖向预应力",
    "side_mid_ratio": "边中跨比", "pier_height": "墩身高度",
    "zero_block": "零号块长度", "material": "主梁材料",
}


def _d5_span_fit_deduction_rigid(L: float) -> float:
    """刚构跨径适配:[80,200] 自由;[50,80)&(200,250] 扣 0~0.5 线性;<50 或 >250 扣 1。"""
    eps = 1e-9
    if L < 50.0 - eps or L > 250.0 + eps:
        return 1.0
    if 80.0 - eps <= L <= 200.0 + eps:
        return 0.0
    if L < 80.0 - eps:
        return _lerp(L, 80.0, 50.0, 0.0, 0.5)
    return _lerp(L, 200.0, 250.0, 0.0, 0.5)


def _d5_side_mid_deduction_rigid(r: float) -> float:
    """刚构边中跨比 r 的扣分:[0.52,0.60] 自由;[0.5,0.52)&(0.6,0.62] 扣 0.2;
    [0.47,0.5)&(0.62,0.7] 扣 0.3~0.8 线性;(0.7,0.75] 扣 0.8;<0.47 或 >0.75 扣 1。"""
    eps = 1e-9
    if 0.52 - eps <= r <= 0.60 + eps:
        return 0.0
    if 0.50 - eps <= r < 0.52 - eps:
        return 0.2
    if 0.60 + eps < r <= 0.62 + eps:
        return 0.2
    if 0.47 - eps <= r < 0.50 - eps:
        return _lerp(r, 0.50, 0.47, 0.3, 0.8)
    if 0.62 + eps < r <= 0.70 + eps:
        return _lerp(r, 0.62, 0.70, 0.3, 0.8)
    if 0.70 + eps < r <= 0.75 + eps:
        return 0.8
    return 1.0


def _d5_pier_ratio_deduction(q: float) -> float:
    """墩高/主跨 q:>=1/10 不扣;[1/12,1/10) 扣 0.2~0.7 线性;[1/15,1/12) 扣 0.8;<1/15 扣 1。"""
    eps = 1e-9
    if q >= 1.0 / 10.0 - eps:
        return 0.0
    if q >= 1.0 / 12.0 - eps:
        return _lerp(q, 1.0 / 10.0, 1.0 / 12.0, 0.2, 0.7)
    if q >= 1.0 / 15.0 - eps:
        return 0.8
    return 1.0


def _d5_pier_abs_deduction(h: float) -> float:
    """绝对墩高:<100m 不扣;100~120m 扣 0.5;>120m 扣 1(难施工)。"""
    if h < 100.0 - 1e-9:
        return 0.0
    if h <= 120.0 + 1e-9:
        return 0.5
    return 1.0


def _d5_steel_ratio_limit_rigid(L: float | None) -> float | None:
    """刚构含筋量上限(kg/m³):[50,70)→50;[70,100)→60;[100,150)→90;[150,200]→130。"""
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


def _d5_material_requirement_rigid(L: float) -> int | None:
    """材料最低等级(刚构):[70,120) → C55;[120,200] → C60;其余跨径不做评判。"""
    eps = 1e-9
    if 70.0 - eps <= L < 120.0 - eps:
        return 55
    if 120.0 - eps <= L <= 200.0 + eps:
        return 60
    return None


def _score_md_d5(
    L: float | None,
    H_mid: float | None,
    total_length: float | None,
    has_vertical_tendon: bool,
    pst_steel_ratio: float | None = None,
    span_lengths: list[float] | None = None,
    pier_heights: list[float] | None = None,
    main_span: float | None = None,
    zero_block_len: float | None = None,
    concrete_grade: int | None = None,
) -> tuple[float, dict[str, Any]]:
    """经济性与合理性(刚构准则,占比 30%;九小项各占 D5 的 10%~20%)。

    数据缺失的小项跳过,按剩余权重归一化;全部缺失 → 跳过给 1.0。
    与连续梁 D5 的差异:跨径适配 80~200m(50~80/200~250 线性扣 0~0.5)、竖向预应力权重 10%、
    边中跨比 0.52~0.60、新增墩身高度小项(原 D6 并入)、材料档 [70,120)/[120,200]。
    竖向预应力判定同连续梁(腹板竖筋 WEBVERTICALREBAR 落支点两侧 L/3 或竖向 PST)。
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

    # 1) 跨径适配(刚构 80~200m;常规适用下限 80m 挂篮经济性,200m 以上极限区间)
    if L is None:
        _put("span_fit", None, "L 缺失,跳过")
    else:
        _put("span_fit", _d5_span_fit_deduction_rigid(L), f"L={L:g} m(适配区间 80~200 m)")

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
        limit = _d5_steel_ratio_limit_rigid(L)
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

    # 6) 边中跨比(三跨布置,左/右边跨分别比中跨,取最不利)
    if not span_lengths or len(span_lengths) < 3:
        _put("side_mid_ratio", None, "跨径序列缺失或非三跨布置,跳过")
    else:
        mid = max(span_lengths)
        ratios = (span_lengths[0] / mid, span_lengths[-1] / mid)
        deds = [_d5_side_mid_deduction_rigid(r) for r in ratios]
        worst = max(deds)
        _put("side_mid_ratio", worst,
             f"边中跨比 {ratios[0]:.3f} / {ratios[1]:.3f}(宜 0.52~0.60,取最不利)")

    # 7) 墩身高度(原 D6 并入):比例 + 绝对高度叠扣,封顶 1
    span_ref = main_span if main_span else L
    if not pier_heights or span_ref is None or span_ref <= 0:
        _put("pier_height", None, "墩高或主跨缺失,跳过")
    else:
        h = max(pier_heights)
        q = h / span_ref
        d_ratio = _d5_pier_ratio_deduction(q)
        d_abs = _d5_pier_abs_deduction(h)
        ded = min(1.0, d_ratio + d_abs)
        _put("pier_height", ded,
             f"墩高={h:.1f} m(墩高/主跨=1/{1.0 / q:.1f},宜 ≥1/10 且 ≤100 m;比例扣 {d_ratio:.2f}+绝对扣 {d_abs:.2f})")

    # 8) 零号块长度
    if zero_block_len is None:
        _put("zero_block", None, "零号块长度缺失(无 0号块 单元组或节点几何),跳过")
    else:
        _put("zero_block", _d5_zero_block_deduction(zero_block_len),
             f"零号块长度={zero_block_len:g} m(宜 9~14 m)")

    # 9) 主梁材料(刚构):[70,120) 需 C55+;[120,200] 需 C60+;其余跨径不评判
    req = _d5_material_requirement_rigid(L) if L is not None else None
    if req is None:
        _put("material", None, "跨径不在评判区间(70~200 m)或 L 缺失,跳过")
    elif concrete_grade is None:
        _put("material", None, "混凝土等级缺失,跳过")
    else:
        _put("material", 0.0 if concrete_grade >= req else 1.0,
             f"C{concrete_grade}(L={L:g} m 要求 ≥C{req})")

    scored = [(k, float(it["score"])) for k, it in items.items() if "score" in it]
    if not scored:
        return 1.0, {"note": "无经济数据,D5 跳过给 1.0", "items": items}
    w_sum = sum(_D5_WEIGHTS_RIGID[k] for k, _ in scored)
    d5 = sum(_D5_WEIGHTS_RIGID[k] * s for k, s in scored) / w_sum
    issues = [
        f"{_D5_ITEM_LABELS_RIGID[k]}:{it['note']}"
        for k, it in items.items()
        if it.get("score", 1.0) < 1.0 - 1e-9
    ]
    return d5, {
        "items": items,
        "weights": dict(_D5_WEIGHTS_RIGID),
        "level": _level_from_score(d5),
        "issue": "; ".join(issues) if issues else None,
        "issues": issues,
    }
# 刚构 MD 五维权重(测试方确认:刚构无 D6,原 D6 边中跨比/墩高并入 D5 小项)
_MD_WEIGHTS_RIGID: dict[str, float] = {
    "D1_H_root": 0.20,
    "D2_H_mid": 0.15,
    "D3_n_H": 0.15,
    "D4_thickness": 0.20,
    "D5_consistency": 0.30,
}


def score_rigid_frame(params: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """变截面连续刚构:MD 5 维(D1~D5 全部切换刚构准则;刚构无 D6)。"""
    L = params["L"]
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
        params.get("pst_steel_ratio"),
        params.get("span_lengths"),
        params.get("pier_heights"),
        params.get("main_span_from_nodes"),
        params.get("zero_block_len"),
        params.get("concrete_grade"),
    )
    return _assemble(params, [
        ("D1_H_root", d1, d1d), ("D2_H_mid", d2, d2d), ("D3_n_H", d3, d3d),
        ("D4_thickness", d4, d4d), ("D5_consistency", d5, d5d),
    ], weights=_MD_WEIGHTS_RIGID)
