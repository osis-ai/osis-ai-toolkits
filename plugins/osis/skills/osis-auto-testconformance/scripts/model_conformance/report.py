"""Markdown report generation for model conformance evaluation."""
from __future__ import annotations

from typing import Any

from .bridges.cantilever import _D4_ITEM_LABELS, _D4_WEIGHTS, _D5_ITEM_LABELS, _D5_WEIGHTS
from .bridges.rigid_frame import _D5_ITEM_LABELS_RIGID, _D5_WEIGHTS_RIGID

_DIM_NAMES: dict[str, str] = {
    "D1_H_root": "D1 支点梁高",
    "D2_H_mid": "D2 跨中梁高",
    "D3_n_H": "D3 悬浇段梁高变化曲线",
    "D4_thickness": "D4 截面常规尺寸合理性判断",
    "D5_consistency": "D5 经济性与合理性",
    "D6_rigid_frame": "D6 刚构边跨比与墩高合理性",
    "D1_span": "D1 跨径适配性",
    "D2_beam_height": "D2 高跨比",
    "D3_section": "D3 截面常规尺寸",
    "D4_stages": "D4 建设期经济性",
    "D4_economy": "D4 建设期经济性",
    "D4_void_ratio": "D4 截面经济性(空心率)",
    "D5_economy": "D5 建设期经济性",
    "D5_standardization": "D5 标准化模板化指标",
    "D5_completeness": "D5 结构完整性",
    "D1": "D1",
    "D2": "D2",
    "D3": "D3",
    "D4": "D4",
    "D5": "D5",
    "D6": "D6",
}


def _report_reasons(detail: dict[str, Any]) -> list[str]:
    """从维度详情中提取扣分原因(多条全列,去重保序)。"""
    raw: list[str] = []
    if "issues" in detail and detail["issues"]:
        raw.extend(str(i) for i in detail["issues"])
    if "issue" in detail and detail["issue"]:
        raw.append(str(detail["issue"]))
    if "note" in detail and detail["note"]:
        raw.append(str(detail["note"]))
    seen: set[str] = set()
    out: list[str] = []
    for r in raw:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


# 维度 → {issue 子串 → 建议}。
# - "DEFAULT" 兜底,fallback 走 dim 默认建议
# - 每条 issue 子串在打分函数里都是字面量,直接当 key 即可
_ISSUE_SUGGESTIONS: dict[str, dict[str, str]] = {
    "D1_H_root": {
        "L 缺失": "未能从节点坐标/支座提取主跨 L,请检查 _5_node.py 与支座或桥墩节点。",
        "H_root 缺失": "请在截面代码中提供根部梁高 H_root。",
        "超出允许区间": "建议调整根部梁高 H_root,使 H_root/L 落回该跨档允许高跨比区间。",
    },
    "D2_H_mid": {
        "超出 60-200m": "建议确认主跨 L 是否在 60~200m 范围内;若为小跨径,请改用对应桥型评分器。",
        "L 缺失": "未能从节点坐标/支座提取主跨 L,请检查 _5_node.py 与支座或桥墩节点。",
        "不在跨中梁高跨径分档表": "请确认主跨 L 是否落在跨中梁高跨径分档表覆盖的区间。",
        "H_mid 缺失": "请在截面代码中提供跨中梁高 H_mid。",
        "超出允许区间": "建议调整跨中梁高 H_mid,使 H_mid/L 落回该跨档允许高跨比区间。",
        "[1.8, 2)": "建议 70m 以下跨径跨中梁高不低于 2.0 m。",
    },
    "D4_thickness": {
        "跨中顶板": "建议跨中顶板厚不小于 0.22 m。",
        "跨中底板": "建议跨中底板厚不小于 0.22 m。",
        "支点顶板": "建议支点附近顶板厚不小于 0.40 m。",
        "横梁底板": "建议 0 号梁段横梁底板厚取根部梁高的 1/4~1/7。",
        # bot_root 标签含“附近底板”；横梁建议键须排在其前，避免 dia issue 误命中。
        "附近底板": "建议支点附近底板厚取根部梁高 1/5~1/12。",
        "跨中腹板": "建议跨中腹板厚取 0.30~0.60 m(连续梁)或 0.30~0.65 m(刚构)。",
        "支点腹板": "建议支点(0 号段)腹板厚取 0.60~1.20 m。",
        "翼缘": "建议翼缘端部厚取 0.12~0.25 m(常用 0.15~0.20 m)。",
        "渐厚": "建议顶/底/腹板厚度自跨中向支点逐渐增大。",
        "< 0.15": "建议跨中底板厚不小于 0.20 m。",
        "< 0.20": "建议跨中底板厚不小于 0.20 m。",
        "<= T_mid": "建议根部底板厚大于跨中底板厚。",
        "局部增大": "建议检查底板厚度沿纵向是否单调递减。",
    },
    "D5_consistency": {
        "跨径适配": "建议主跨 L 取 50~160 m(连续梁)或 80~200 m(刚构)经济区间。",
        "全联总长": "建议全联总长不超过 1000 m(联长过长温度效应巨大)。",
        "最小梁高": "建议所有截面梁高不小于 2.2 m(保证箱内作业空间)。",
        "含筋量": "建议纵向钢束含筋量不低于 35 kg/m³,且不超过所在跨档上限(50~70m:50;70~100m:60;100~150m:90;150~200m:130 kg/m³)。",
        "竖向预应力": "建议在支点两侧 L/3 范围内截面设置 WEBVERTICALREBAR 腹板竖筋。",
        "边中跨比": "建议边中跨比取 0.62~0.75(连续梁)或 0.52~0.60(刚构),以最不利一侧计。",
        "墩身高度": "建议墩高不小于主跨 1/10,且绝对墩高不超过 100 m(100~120 m 扣 0.5、超 120 m 扣 1)。",
        "零号块": "建议零号块长度取 9~14 m。",
        "主梁材料": "建议主梁混凝土:连续梁 [60,120)m 用 C55+、[120,170]m 用 C60+;刚构 [70,120)m 用 C55+、[120,200]m 用 C60+。",
        "超出": "建议确认主跨 L 是否在合理范围内(连续梁 50~200m / 刚构 50~250m);若为小跨径,请改用对应桥型评分器。",
        "H_root": "建议确保根部梁高 H_root 大于跨中梁高 H_mid。",
        "H_mid": "建议跨中梁高 H_mid 不小于 2.2 m。",
    },
    "D6_rigid_frame": {
        "边跨/主跨比": "建议将边跨/主跨比调整到 0.52~0.60 区间。",
        "墩高": "建议确保墩高/主跨比 ≥ 1/10,且绝对墩高不超过 120 m。",
        "跨径布置": "建议检查节点坐标,确保能提取桥墩位置与梁端位置。",
    },
    "D5_completeness": {
        "节点数": "建议增加节点数量(至少 5 个)。",
        "单元": "建议定义单元(engine.element.create)。",
        "边界": "建议定义边界条件(engine.boundary.create)。",
        "阶段数": "建议定义至少 2 个施工阶段。",
    },
    "D1_span": {
        "提取跨径": "请检查节点与支座:主梁轴线节点、偏轴支座/桥墩节点,或 boundary.assign 约束节点。",
        "未能提供跨径": "请检查节点与支座:主梁轴线节点、偏轴支座/桥墩节点,或 boundary.assign 约束节点。",
    },
    "D2_beam_height": {
        "L 或 H 缺失": "主跨 L 从节点/支座提取失败,或截面未给出梁高 H。请检查 _5_node.py 与 _4_section.py。",
    },
}

# 维度 → 兜底建议
_DIM_DEFAULT_SUGGESTION: dict[str, str] = {
    "D1_H_root": "建议调整根部梁高 H_root,使高跨比落在该跨档允许区间 {expected_band}。",
    "D2_H_mid": "建议调整跨中梁高 H_mid,使高跨比落在该跨档允许区间 {expected_band}。",
    "D3_n_H": "建议按主跨选取悬浇段梁高曲线幂次:连续梁 [50,70)m 取 1~3 次均可、[70,100]m 优选 2 次(1.8 不扣)、[100,150]m 优选 1.8 次(2.0 不扣)、(150,200]m 优选 1.5 次、>200m 直接扣分;刚构 [70,100]m 优选 2 次(1.8 不扣)、[120,150]m 优选 1.8 次(2.0 不扣)、(150,250]m 优选 1.5 次、>250m 直接扣分。",
    "D4_thickness": "建议核对截面常规尺寸:跨中顶/底板 ≥0.22 m、支点顶板 ≥0.40 m、支点附近底板取根部梁高 1/5~1/12、0 号段横梁底板 1/4~1/7、腹板跨中 0.30~0.60 m(连续梁)/0.30~0.65 m(刚构)、支点 0.60~1.20 m、翼缘端部 0.12~0.25 m,且自跨中向支点逐渐增厚。",
    "D5_consistency": "建议核对经济性各小项:跨径适配(连续梁 50~160 m / 刚构 80~200 m)、全联总长 ≤1000 m、所有截面梁高 ≥2.2 m、含筋量 ≥35 kg/m³ 且不超跨档上限、L>75 m 设竖向预应力、边中跨比 0.62~0.75(连续梁)/0.52~0.60(刚构)、墩高 ≥1/10 主跨且 ≤100 m(刚构)、零号块 9~14 m、主梁混凝土达标。",
    "D6_rigid_frame": "建议检查连续刚构边跨比(0.52~0.60)与墩高(≥1/10 主跨、且≤120 m)。",
    "D1_span": "建议将跨径 L 调整到该体系合理区间 {valid_range} m。",
    "D2_beam_height": "建议调整梁高,使 H/L 落在合理区间(各桥型不同;详见报告)。",
    "D3_section": "建议按对应标准调整截面:标准T查腹板/翼缘/悬臂/马蹄;矮T查腹板厚/翼缘端厚/梗斜,并保证支点段不小于跨中。",
    "D4_stages": "建议混凝土折算厚度落在合理带(标准T 0.35~0.65 / 矮T 0.28~0.46)、钢绞线用量合理(标准T 30~50 / 矮T 18~38 kg/m³)、梁宽合理(标准T 1.6~2.3 / 矮T 1.0~1.55),并含预制/存梁/二期/徐变≥4 个施工阶段。",
    "D4_economy": "建议混凝土折算厚度和钢绞线用量落在合理区间(各桥型不同)。",
    "D4_void_ratio": "建议将空心率控制在 0.45~0.52(可用区间约 0.40~0.55)。",
    "D5_economy": "建议将混凝土折算厚度控制在 0.25~0.5 m³/m²、板宽 1.0~2.0 m,并含预制/存梁/二期/徐变≥4 个施工阶段。",
    "D5_standardization": "建议梁宽落在该桥型合理带(小箱梁 2.0~3.2m / 标准T梁 1.6~2.3m / 矮T梁 1.0~1.55m),并含预制/存梁/二期/徐变≥4 个施工阶段。",
    "D5_completeness": "建议检查模型结构完整性。",
}


def _issue_suggestion(dim: str, issue: str) -> str | None:
    """单条 issue 文本 → 建议(字典查表;没命中 → None,留给 fallback)。"""
    table = _ISSUE_SUGGESTIONS.get(dim) or {}
    for needle, advice in table.items():
        if needle in issue:
            return advice
    return None


def _fallback_suggestion(dim: str, detail: dict[str, Any]) -> str:
    """没有命中 issue → 用 detail 里的 expected / range 字段拼一条具体建议。"""
    tmpl = _DIM_DEFAULT_SUGGESTION.get(dim, "建议按上述期望参数调整。")
    # 仅在模板含 {valid_range}/{expected_band}/{expected_type}/{threshold} 时格式化
    if "{" not in tmpl:
        return tmpl
    try:
        return tmpl.format(
            valid_range=detail.get("valid_range"),
            expected_band=detail.get("expected_band"),
            expected_type=detail.get("expected_type"),
            threshold=detail.get("threshold"),
        )
    except (KeyError, IndexError):
        return tmpl


def _report_suggestion(dim: str, detail: dict[str, Any], btype: str = "") -> str:
    """根据维度和详情给出改进建议。"""
    # 1) D3_n_H 的中性分走专属文案(D3 没有 issue 字段)
    if dim == "D3_n_H" and detail.get("level") == "neutral":
        return "n_H 由离散截面隐含,如需校验,请在项目画像中显式给出 n_H 或拟合节点数据。"

    # 2) D1_H_root / D2_H_mid 的「期望值已知」分支(没 issue 但有 expected)
    if dim in ("D1_H_root", "D2_H_mid") and "issue" not in (detail or {}):
        if dim == "D1_H_root":
            return f"建议将根部梁高 H_root 调整为 {detail.get('expected')} m。"
        return f"建议将跨中梁高 H_mid 调整为 {detail.get('expected')} m。"

    # 2.5) D4_economy / D5_standardization 按桥型定制建议
    if dim == "D4_economy" and btype:
        ranges = {
            "precast_small_box": ("0.37~0.65", "25~46"),
            "t_girder": ("0.35~0.65", "30~50"),
            "hollow_slab": ("0.25~0.55", "25~49"),
        }
        if btype in ranges:
            cr, sr = ranges[btype]
            return (f"建议混凝土折算厚度落在 {cr} m³/m²、"
                    f"钢绞线用量落在 {sr} kg/m³。")

    if dim == "D5_standardization" and btype:
        widths = {
            "precast_small_box": "2.0~3.2",
            "t_girder": "1.0~1.55" if detail.get("t_variant") == "low" else "1.6~2.3",
        }
        if btype in widths:
            return (f"建议梁宽落在 {widths[btype]} m,并含预制/存梁/二期/徐变≥4 个施工阶段。")

    # 3) issues 列表型维度(D4_thickness / D5_consistency / D5_completeness)
    issues = detail.get("issues") or []
    if issues and dim in _ISSUE_SUGGESTIONS:
        advice = _issue_suggestion(dim, "\n".join(str(i) for i in issues))
        if advice is not None:
            return advice

    # 4) issue 字符串型维度(D1 / D2)
    issue_str = detail.get("issue") or ""
    if issue_str and dim in _ISSUE_SUGGESTIONS:
        advice = _issue_suggestion(dim, issue_str)
        if advice is not None:
            return advice

    # 5) 兜底
    return _fallback_suggestion(dim, detail)


def generate_report(result: dict[str, Any], candidate_name: str = "") -> str:
    """从 model_conformance.evaluate 的返回结果生成 Markdown 详细报告。

    按 D1~D6 顺序逐项说明，满分项只标注"符合要求"，不展开。
    """
    cand = result.get("candidate", {})
    params = cand.get("params", {})
    dims = cand.get("dimensions", {})
    total = cand.get("total_score", cand.get("total_score_5", 0.0))
    max_dim = cand.get("max_dim", 5)
    rating = cand.get("rating", "")
    btype = result.get("bridge_type") or cand.get("bridge_type", "?")
    L = params.get("L")
    Hr = params.get("H_root")
    Hm = params.get("H_mid")
    Tr = params.get("T_root")
    Tm = params.get("T_mid")
    sc = params.get("stage_count")
    ref_score = result.get("reference_score")
    ratio = result.get("ratio", {}).get("candidate_over_reference")

    title = f"{candidate_name} 构造建模正确性评定报告" if candidate_name else "构造建模正确性评定报告"
    lines = [f"# {title}", ""]

    lines.append("## 项目概况")
    if candidate_name:
        lines.append(f"- 候选目录：{candidate_name}")
    lines.append(f"- 桥型：{btype}")
    tv = cand.get("t_variant")
    if tv:
        tv_label = {"standard": "标准 T 梁(大T)", "low": "矮 T 梁"}.get(tv, tv)
        lines.append(f"- 梁型分类：{tv_label}")
    if L is not None:
        lines.append(f"- 主跨 L：{L} m")
    if Hr is not None:
        lines.append(f"- 根部梁高 H_root：{Hr} m")
    if Hm is not None:
        lines.append(f"- 跨中梁高 H_mid：{Hm} m")
    if Tr is not None or Tm is not None:
        lines.append(f"- 底板厚：T_root={Tr if Tr is not None else '-'} m, T_mid={Tm if Tm is not None else '-'} m")
    if sc is not None:
        lines.append(f"- 阶段数：{sc}")
    lines.append(f"- 总分：{total:.2f} / {max_dim:.1f}")
    lines.append(f"- 评级：{rating}")
    if ref_score is not None and ratio is not None:
        lines.append(f"- 与 reference 比值：{ratio:.4f}")
    lines.append("")

    lines.append("## 分项检查")
    lines.append("")

    for idx, (dim_name, dim_detail) in enumerate(dims.items(), start=1):
        dim_title = _DIM_NAMES.get(dim_name) or dim_name
        score = dim_detail.get("score_5", 0.0)
        level = dim_detail.get("level", "")
        lines.append(f"### {idx}. {dim_title}：{score:.2f} / 1.0")
        lines.extend(_dim_context_lines(dim_name, dim_detail))

        reasons = _report_reasons(dim_detail)
        if score >= 1.0:
            lines.append("- 状态：符合要求")
        elif score == 0.5 and level == "neutral":
            lines.append("- 状态：中性分")
            if reasons:
                lines.append(f"- 说明：{reasons[0]}")
        else:
            lines.append("- 状态：不符合")
            if reasons:
                lines.append(f"- 原因：{'；'.join(reasons)}")
            lines.append(f"- 建议：{_report_suggestion(dim_name, dim_detail, btype)}")
        lines.append("")

    return "\n".join(lines)


def _dim_context_lines(dim_name: str, detail: dict[str, Any]) -> list[str]:
    """按维度输出关键量（实际值 / 期望值 / 允许范围等）。"""
    lines: list[str] = []
    if dim_name == "D1_H_root":
        if detail.get("actual") is not None:
            lines.append(f"- 实际 H_root：{detail['actual']} m")
        if detail.get("ratio"):
            lines.append(f"- 实际高跨比：{detail['ratio']}")
        if detail.get("allowed_range"):
            std = detail.get("std_span")
            suffix = f"（按 {std:g} m 跨档）" if std else ""
            lines.append(f"- 允许高跨比：{detail['allowed_range']}{suffix}")
        if detail.get("deduction") is not None and detail.get("issue"):
            lines.append(f"- 偏差扣分：{detail['deduction']}")
        if detail.get("expected") is not None:
            lines.append(f"- 期望 H_root：{detail['expected']} m")
        if detail.get("diff") is not None:
            lines.append(f"- 偏差：{detail['diff']} m")
    elif dim_name == "D2_H_mid":
        if detail.get("actual") is not None:
            lines.append(f"- 实际 H_mid：{detail['actual']} m")
        if detail.get("ratio"):
            lines.append(f"- 实际高跨比：{detail['ratio']}")
        if detail.get("allowed_range"):
            std = detail.get("std_span")
            suffix = f"（按 {std:g} m 跨档）" if std else ""
            lines.append(f"- 允许范围：{detail['allowed_range']}{suffix}")
        if detail.get("deduction") is not None and detail.get("issue"):
            lines.append(f"- 偏差扣分：{detail['deduction']}")
        if detail.get("expected") is not None:
            lines.append(f"- 期望 H_mid：{detail['expected']} m")
        if detail.get("diff") is not None:
            lines.append(f"- 偏差：{detail['diff']} m")
    elif dim_name == "D3_n_H":
        if detail.get("actual") is not None:
            lines.append(f"- 实际 n_H：{detail['actual']}")
        if detail.get("expected_band"):
            pref = detail.get("preferred")
            pref_s = f"（优值 {pref} 次）" if pref else ""
            lines.append(f"- 分档：{detail['expected_band']}{pref_s}")
        if detail.get("deduction") is not None and detail.get("issue"):
            lines.append(f"- 扣分：{detail['deduction']}")
    elif dim_name == "D4_thickness":
        items = detail.get("items") or {}
        if items:
            detail_weights = detail.get("weights") or {}
            for key, it in items.items():
                label = _D4_ITEM_LABELS.get(key, key)
                w = detail_weights.get(key, _D4_WEIGHTS.get(key))
                w_s = f"（权重 {w:.0%}）" if w is not None else ""
                if it.get("skipped"):
                    lines.append(f"- {label}{w_s}：跳过，{it.get('note', '')}")
                else:
                    lines.append(f"- {label}{w_s}：得分 {it.get('score', 0.0):.2f}，{it.get('note', '')}")
        elif detail.get("note"):
            lines.append(f"- {detail['note']}")
        elif "T_root" in detail or "T_mid" in detail:
            lines.append(f"- T_root = {detail.get('T_root', '-')} m, T_mid = {detail.get('T_mid', '-')} m")
    elif dim_name == "D5_consistency":
        items = detail.get("items") or {}
        if items:
            detail_weights = detail.get("weights") or {}
            for key, it in items.items():
                label = _D5_ITEM_LABELS.get(key) or _D5_ITEM_LABELS_RIGID.get(key, key)
                w = detail_weights.get(key)
                if w is None:
                    w = _D5_WEIGHTS.get(key) if key in _D5_WEIGHTS else _D5_WEIGHTS_RIGID.get(key)
                w_s = f"（权重 {w:.0%}）" if w is not None else ""
                if it.get("skipped"):
                    lines.append(f"- {label}{w_s}：跳过，{it.get('note', '')}")
                else:
                    lines.append(f"- {label}{w_s}：得分 {it.get('score', 0.0):.2f}，{it.get('note', '')}")
        elif detail.get("note"):
            lines.append(f"- {detail['note']}")
        elif detail.get("L") is not None:
            lines.append(f"- 主跨 L：{detail['L']} m")
    elif dim_name == "D6_rigid_frame":
        if detail.get("side_spans") is not None:
            lines.append(f"- 边跨：{detail['side_spans']} m")
        if detail.get("main_span") is not None:
            lines.append(f"- 主跨(节点提取)：{detail['main_span']} m")
        if detail.get("side_to_main_ratio") is not None:
            lines.append(f"- 边跨/主跨比：{detail['side_to_main_ratio']}")
        if detail.get("pier_heights") is not None:
            lines.append(f"- 墩高：{detail['pier_heights']} m")
    elif dim_name == "D1_span":
        if detail.get("actual") is not None:
            lines.append(f"- 实际跨径 L：{detail['actual']} m")
        if detail.get("girder_system"):
            lines.append(f"- 梁体体系：{detail['girder_system']}")
        if detail.get("valid_range"):
            lines.append(f"- 合理区间：{detail['valid_range']} m")
        if detail.get("band"):
            lines.append(f"- 分档：{detail['band']}")
        if detail.get("deduction") is not None and detail.get("deduction"):
            lines.append(f"- 扣分：{detail['deduction']}")
    elif dim_name == "D2_beam_height":
        if detail.get("H") is not None:
            lines.append(f"- 梁高 H：{detail['H']} m")
        if detail.get("L") is not None:
            lines.append(f"- 跨径 L：{detail['L']} m")
        if detail.get("L_over_H") is not None:
            lines.append(f"- L/H：{detail['L_over_H']}")
        elif detail.get("H_over_L") is not None:
            lines.append(f"- H/L：{detail['H_over_L']}")
        if detail.get("girder_system"):
            lines.append(f"- 梁体体系：{detail['girder_system']}")
        if detail.get("expected_band"):
            label = "合理 L/H 区间" if detail.get("L_over_H") is not None else "合理 H/L 区间"
            lines.append(f"- {label}：{detail['expected_band']}")
        if detail.get("band"):
            lines.append(f"- 分档：{detail['band']}")
        if detail.get("deduction") is not None and detail.get("deduction"):
            lines.append(f"- 扣分：{detail['deduction']}")
    elif dim_name == "D3_section":
        if detail.get("girder_system"):
            lines.append(f"- 梁体体系：{detail['girder_system']}")
        if detail.get("mid_name"):
            lines.append(f"- 跨中截面：{detail['mid_name']}")
        for key, label in (
            ("tw", "腹板厚 tw"),
            ("tt1", "翼缘端部厚 tt1"),
            ("tt2", "翼缘根部厚 tt2"),
            ("tt2_over_h", "翼缘根部厚/梁高"),
            ("cantilever", "单侧悬臂 Bm-Tw/2"),
            ("bs", "边翼缘宽 bs"),
            ("bh", "马蹄宽 bh"),
            ("bh_over_tw", "马蹄宽/腹板厚"),
            ("web_slenderness", "腹板净高/厚度"),
        ):
            if detail.get(key) is not None:
                lines.append(f"- {label}：{detail[key]}")
        if detail.get("support_name"):
            lines.append(f"- 支点截面：{detail['support_name']}")
        if detail.get("deduction") is not None and detail.get("deduction"):
            lines.append(f"- 扣分合计：{detail['deduction']}")
        if detail.get("section_types"):
            lines.append(f"- 截面类型：{detail['section_types']}")
        if detail.get("girder_section_count") is not None:
            lines.append(f"- 主梁截面数：{detail['girder_section_count']}")
        if detail.get("expected_type"):
            lines.append(f"- 期望类型：{detail['expected_type']}")
    elif dim_name == "D4_void_ratio":
        if detail.get("void_ratio") is not None:
            lines.append(f"- 空心率：{detail['void_ratio']}")
        if detail.get("deduction") is not None and detail.get("deduction"):
            lines.append(f"- 扣分：{detail['deduction']}")
    elif dim_name in ("D4_stages", "D4_economy", "D5_economy"):
        if detail.get("concrete_ratio") is not None:
            lines.append(f"- 混凝土折算厚度：{detail['concrete_ratio']} m³/m²")
        if detail.get("pst_steel_ratio") is not None:
            lines.append(f"- 预应力钢绞线用量：{detail['pst_steel_ratio']} kg/m³")
    elif dim_name == "D5_standardization":
        if detail.get("beam_width") is not None:
            lines.append(f"- 梁宽/板宽：{detail['beam_width']} m")
        if detail.get("stage_count") is not None:
            lines.append(f"- 阶段数：{detail['stage_count']}")
        if detail.get("stage_names"):
            lines.append(f"- 阶段名：{detail['stage_names']}")
        if detail.get("threshold") is not None:
            lines.append(f"- 阈值：≥{detail['threshold']}")
        if detail.get("deduction") is not None and detail.get("deduction"):
            lines.append(f"- 扣分合计：{detail['deduction']}")
    elif dim_name == "D5_completeness":
        if detail.get("node_count") is not None:
            lines.append(f"- 节点数：{detail['node_count']}")
        if detail.get("element_count") is not None:
            lines.append(f"- 单元数：{detail['element_count']}")
        if detail.get("boundary_count") is not None:
            lines.append(f"- 边界数：{detail['boundary_count']}")
        if detail.get("stage_count") is not None:
            lines.append(f"- 阶段数：{detail['stage_count']}")
    return lines
