"""桥梁构造建模正确性评定 — 按 **桥型分发**,每类一套规则。

目录:
  common.py / report.py     共享提取与报告
  bridges/                  各桥型评分器(一层一桥型)
    cantilever.py           悬浇梁 D1–D5
    rigid_frame.py          连续刚构 D1–D6
    t_girder.py             简支 T 梁 D1–D4
    small_box.py            简支小箱梁 D1–D4
    hollow_slab.py          简支空心板 D1–D5
    cast_in_place.py        现浇箱梁(简化 5 维)
    unknown.py              未知桥型兜底

规则来源:悬浇梁 Skill / AI 经济性合理性评判标准(T梁/小箱梁/空心板)。
**不读 .out**,只读 candidate 目录 .py,AST 提取后按 bridge_type 路由。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

try:
    from ..generic_text import collect_python_files
    from ..registry import register
except ImportError:
    # .agents 独立副本无框架:collect_python_files 用 .common 内嵌实现,register 退化为恒等装饰器
    from .common import collect_python_files

    def register(_name):
        return lambda f: f

from .bridges import (
    score_cast_in_place,
    score_hollow_slab,
    score_rigid_frame,
    score_small_box,
    score_t_girder,
    score_unknown,
    score_variable_section,
)
from .common import (
    _extract_params,
    _has_vertical_tendon,
    detect_bridge_type,
    spans_from_name,
)
from .report import generate_report

SCORERS: dict[str, Callable[[dict[str, Any]], tuple[float, dict[str, Any]]]] = {
    "cantilever_box": score_variable_section,
    "rigid_frame": score_rigid_frame,
    "t_girder": score_t_girder,
    "precast_small_box": score_small_box,
    "cast_in_place_box": score_cast_in_place,
    "hollow_slab": score_hollow_slab,
    "unknown": score_unknown,
}


def _score_one(
    files: dict[str, str],
    *,
    bridge_type: str,
    expected_L: float | None,
    is_continuous: bool | None,
    is_prestressed: bool | None = None,
    concrete_ratio: float | None = None,
    beam_width: float | None = None,
) -> tuple[float, dict[str, Any]]:
    """纯计算:从代码提取测量值 + 调用方注入的意图参数 → 选评分器 → 出分。

    主跨 L 以节点/支座几何为准;expected_L 仅在节点提取失败时作兜底,不从目录名推断。
    """
    params = _extract_params(files)
    params["bridge_type"] = bridge_type
    if params.get("L") is None and expected_L is not None:
        params["L"] = expected_L
    if is_continuous is None:
        is_continuous = params["stage_count"] >= 4
    params["is_continuous"] = is_continuous
    if is_prestressed is not None:
        params["is_prestressed"] = bool(is_prestressed)
    if concrete_ratio is not None:
        params["concrete_ratio"] = float(concrete_ratio)
    if beam_width is not None:
        params["beam_width"] = float(beam_width)

    # 竖向预应力:按支点两侧 L/3 + WEBVERTICALREBAR 重判
    params["has_vertical_tendon"] = _has_vertical_tendon(
        files,
        L=params.get("L"),
        support_xs=params.get("support_xs") or [],
    )

    scorer = SCORERS.get(bridge_type, score_unknown)
    overall, details = scorer(params)
    details["bridge_type"] = bridge_type
    return overall, details


@register("model_conformance")
def evaluate(
    reference_root: Any,
    candidate_root: Path,
    *,
    system_config: dict[str, Any],
    resources: dict[str, Any],
) -> dict[str, Any]:
    """候选代码评分;bridge_type 由 resources 传入。主跨 L 从节点提取。"""
    del system_config

    if not isinstance(candidate_root, Path) or not candidate_root.is_dir():
        return {"overall_score": 0.0, "skipped": True, "reason": "candidate_root 不存在或不是目录"}

    bridge_type = resources.get("bridge_type")
    if not bridge_type:
        return {
            "overall_score": 0.0,
            "skipped": True,
            "reason": "resources 未提供 bridge_type —— 本指标不做桥型推断,需调用方传入",
        }

    expected_L = resources.get("expected_L")
    is_continuous = resources.get("is_continuous")
    is_prestressed = resources.get("is_prestressed")
    concrete_ratio = resources.get("concrete_ratio")
    beam_width = resources.get("beam_width")
    if isinstance(expected_L, (int, float)) and not isinstance(expected_L, bool):
        expected_L = float(expected_L)
    else:
        expected_L = None
    if is_prestressed is not None:
        is_prestressed = bool(is_prestressed)
    if isinstance(concrete_ratio, (int, float)) and not isinstance(concrete_ratio, bool):
        concrete_ratio = float(concrete_ratio)
    else:
        concrete_ratio = None
    if isinstance(beam_width, (int, float)) and not isinstance(beam_width, bool):
        beam_width = float(beam_width)
    else:
        beam_width = None

    candidate_files: dict[str, str] = resources.get("candidate_files") or collect_python_files(candidate_root)
    if not candidate_files:
        return {"overall_score": 0.0, "skipped": True, "reason": "candidate 下没有 .py 文件"}

    cand_score, cand_details = _score_one(
        candidate_files,
        bridge_type=bridge_type,
        expected_L=expected_L,
        is_continuous=is_continuous,
        is_prestressed=is_prestressed,
        concrete_ratio=concrete_ratio,
        beam_width=beam_width,
    )
    result: dict[str, Any] = {"candidate_score": cand_score, "candidate": cand_details}

    if isinstance(reference_root, Path) and reference_root.is_dir():
        ref_files = collect_python_files(reference_root)
        if ref_files:
            ref_score, ref_details = _score_one(
                ref_files,
                bridge_type=bridge_type,
                expected_L=expected_L,
                is_continuous=is_continuous,
                is_prestressed=is_prestressed,
                concrete_ratio=concrete_ratio,
                beam_width=beam_width,
            )
            ratio = cand_score / ref_score if ref_score > 0.01 else None
            clamped = max(0.0, min(1.0, ratio)) if ratio is not None else 0.0
            result.update({
                "overall_score": clamped,
                "reference_score": ref_score,
                "reference": ref_details,
                "ratio": {"candidate_over_reference": ratio, "clamped_to_0_1": clamped},
            })
        else:
            result["overall_score"] = cand_score
            result["reference"] = {"reason": "reference 下没有 .py 文件"}
    else:
        result["overall_score"] = cand_score

    result["report"] = generate_report(result, candidate_root.name)
    return result


__all__ = [
    "evaluate",
    "collect_python_files",
    "detect_bridge_type",
    "spans_from_name",
    "_has_vertical_tendon",
    "score_variable_section",
    "score_rigid_frame",
    "score_t_girder",
    "score_small_box",
    "score_hollow_slab",
    "score_cast_in_place",
    "SCORERS",
]
