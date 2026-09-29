"""Shared AST extraction helpers and parameter aggregation for model conformance."""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Callable

IGNORED_DIRS = {"__pycache__", ".git", ".venv", "venv", "env"}


def collect_python_files(root: Path) -> dict[str, str]:
    """Collect Python files under a project directory.

    Paths are returned with POSIX separators so reports are stable on Windows.
    (.agents 内嵌副本的 test_conformance  runner 依赖此函数,勿删。)
    """

    root = root.resolve()
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*.py")):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        files[rel] = path.read_text(encoding="utf-8", errors="replace")
    return files


_L_VALID = (50.0, 200.0)
def _lerp(x: float, x0: float, x1: float, y0: float, y1: float) -> float:
    """线性插值: x0 -> y0, x1 -> y1; 允许 x1 < x0。"""
    if x1 == x0:
        return (y0 + y1) / 2.0
    t = (x - x0) / (x1 - x0)
    return y0 + t * (y1 - y0)


def _level_from_score(score: float) -> str:
    """根据得分返回 level: ok / warn / fail; 边界处用 1e-9 容差。"""
    if score >= 0.9 - 1e-9:
        return "ok"
    if score >= 0.5 - 1e-9:
        return "warn"
    return "fail"
_H_RANGE = (0.5, 15.0)      # 合理梁高范围 m
_TB_RANGE = (0.05, 5.0)     # 板件厚度提取范围 m；大跨刚构支点底板可超过 1.5 m


def _is_section_call(node: ast.Call) -> bool:
    """匹配 engine.section.create / create_xxx(...)。"""
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    base = ast.unparse(func.value) if hasattr(ast, "unparse") else None
    return base == "engine.section" and func.attr.startswith("create")


def _const_value(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = _const_value(node.operand)
        if isinstance(v, (int, float)):
            return -v
    return None


def _kw_float(node: ast.Call, key: str) -> float | None:
    for kw in node.keywords:
        if kw.arg == key:
            v = _const_value(kw.value)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return float(v)
    return None


def _kw_str(node: ast.Call, key: str) -> str | None:
    for kw in node.keywords:
        if kw.arg == key:
            v = _const_value(kw.value)
            if isinstance(v, str):
                return v
    return None


def _arg_float(args: list[ast.AST], idx: int) -> float | None:
    if idx < 0 or idx >= len(args):
        return None
    v = _const_value(args[idx])
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    return None


def _extract_section(node: ast.Call) -> dict[str, Any] | None:
    """从任一 engine.section.create_xxx(...) 提取截面参数。

    兼容两种 API + 多种截面类型:
      旧 .xskill:create_conventionalbox(name, h, top_w, bot_w, lw_h, rw_h, web_t, tb, ...)
      新 .agents:create(no, name, "TYPE", [girder_pos], h, ...)

    h 提取策略:跳过开头所有字符串参数(name / type / 可选 girder_pos),
    取其后第一个落在 [0.5, 15] 的数值 —— 适配 CONVENTIONALBOX(h 在 type 后)
    与 TGIRDER/SMALLBOX(h 在 girder_pos 后)。
    tb 仅对箱梁类型在已知位置提取(CONVENTIONALBOX)。
    TGIRDER 另提取 bs/tt1/tt2/tw/bh/hh(跨中标准段尺寸评价用)。
    no 取开头第一个整数(新 API);旧 API 无 no 时为 None。
    """
    args = node.args
    if not args:
        return None
    func_attr = node.func.attr if isinstance(node.func, ast.Attribute) else ""
    # 跳过开头连续的字符串参数
    i = 0
    name = None
    sec_type = None
    girder_pos: str | None = None
    no_val: int | None = None
    while i < len(args):
        v = _const_value(args[i])
        if isinstance(v, str):
            if name is None:
                name = v
            elif sec_type is None and v.isupper():
                sec_type = v
            elif v.lower() in ("left", "middle", "right"):
                girder_pos = v
            i += 1
        elif isinstance(v, int):
            # 新 API 的 no(整数)在开头 —— 记录第一个,后续跳过
            if no_val is None:
                no_val = v
            i += 1
        else:
            break

    if sec_type is None and func_attr.lower() in ("create_tgirder",):
        sec_type = "TGIRDER"
    name = name or _kw_str(node, "name")
    if girder_pos is None:
        girder_pos = _kw_str(node, "girder_pos") or _kw_str(node, "eGirderPos")

    # h:跳过的字符串/整数后,第一个落在合理范围的数值;也接受关键字 h=
    h_val: float | None = None
    if i < len(args):
        v = _const_value(args[i])
        if isinstance(v, (int, float)) and _H_RANGE[0] <= v <= _H_RANGE[1]:
            h_val = float(v)
    if h_val is None:
        hv = _kw_float(node, "h")
        if hv is not None and _H_RANGE[0] <= hv <= _H_RANGE[1]:
            h_val = hv

    # tb:仅箱梁。新 API CONVENTIONALBOX:Tb(底板厚)在 H 之后第 7 个数值位
    # (H, BtL, BtR, BbL, BbR, Bs, Tt, Tb, Tw1, Tw2, ...) → index i+7
    # Tt(顶板厚) → index i+6
    tb_val: float | None = None
    tt_val: float | None = None
    web_t_val: float | None = None
    if sec_type in ("CONVENTIONALBOX", "CONVENTIONAL") and h_val is not None:
        tt_idx = i + 6
        if tt_idx < len(args):
            v = _const_value(args[tt_idx])
            if isinstance(v, (int, float)) and _TB_RANGE[0] <= v <= _TB_RANGE[1]:
                tt_val = float(v)
        tb_idx = i + 7
        if tb_idx < len(args):
            v = _const_value(args[tb_idx])
            if isinstance(v, (int, float)) and _TB_RANGE[0] <= v <= _TB_RANGE[1]:
                tb_val = float(v)
    # Tc(悬臂端部厚):右/左两组悬臂参数 (Bl, Tc, x1, y1, z1) 的第 2 个数
    # → 右 Tc 在 i+30,左 Tc 在 i+36(两组间有 1 个整数 flag 隔开)
    tc_r_val: float | None = None
    tc_l_val: float | None = None
    # 面积估算用:顶/底板宽、中腹板、悬臂长、倒角(宽,高)
    bt_l = bt_r = bb_l = bb_r = tw2_val = None
    bc_l_val = bc_r_val = None
    box_chamfers: list[tuple[float, float]] = []
    if sec_type in ("CONVENTIONALBOX", "CONVENTIONAL") and h_val is not None:
        for idx, name_t in ((i + 30, "tc_r"), (i + 36, "tc_l")):
            if idx < len(args):
                v = _const_value(args[idx])
                if isinstance(v, (int, float)) and _TB_RANGE[0] <= v <= _TB_RANGE[1]:
                    if name_t == "tc_r":
                        tc_r_val = float(v)
                    else:
                        tc_l_val = float(v)
        web_t_idx = i + 8
        if web_t_idx < len(args):
            v = _const_value(args[web_t_idx])
            if isinstance(v, (int, float)) and _TB_RANGE[0] <= v <= _TB_RANGE[1]:
                web_t_val = float(v)
        bt_l, bt_r = _arg_float(args, i + 1), _arg_float(args, i + 2)
        bb_l, bb_r = _arg_float(args, i + 3), _arg_float(args, i + 4)
        tw2_v = _arg_float(args, i + 9)
        if tw2_v is not None and _TB_RANGE[0] <= tw2_v <= _TB_RANGE[1]:
            tw2_val = tw2_v
        # 单箱布局确定:i+10 箱室数=1,4 个箱室宽度后 7 组倒角 + 两组悬臂
        n_cell = _const_value(args[i + 10]) if i + 10 < len(args) else None
        if n_cell == 1:
            for w_off, h_off in ((15, 16), (17, 18), (19, 20), (21, 22),
                                 (23, 24), (25, 26), (27, 28)):
                w = _arg_float(args, i + w_off)
                hh = _arg_float(args, i + h_off)
                if w is not None and hh is not None and w > 0 and hh > 0:
                    box_chamfers.append((w, hh))
            bc_r_val = _arg_float(args, i + 29)
            bc_l_val = _arg_float(args, i + 35)

    # 预制梁几何字段(相对 h 所在索引 i 的偏移)
    # TGIRDER: h,bs,bm,bc,tt1,tt2,x,tw,bh,hh,yh,...
    # SMALLBOX: h,bs,bm,bc,bb,tt,tb,tw,i,tc,tc1,x,xi1,tt1,xi2,yi2,...
    # HOLLOWSLAB: h,bs,bm,bj,tt,tb,tw,tc,tc1,bc,xi1,yi1,xi2,yi2,...
    geo: dict[str, float | None] = {
        "bs": None, "bm": None, "bc": None, "bb": None, "bj": None,
        "tt": None, "tt1": None, "tt2": None, "tb": None, "tw": None,
        "bh": None, "hh": None, "x": None, "yh": None,
        "xi1": None, "yi1": None, "xi2": None, "yi2": None,
    }
    if sec_type is None and func_attr.lower() in ("create_smallbox",):
        sec_type = "SMALLBOX"
    if sec_type is None and func_attr.lower() in ("create_hollowslab",):
        sec_type = "HOLLOWSLAB"

    if sec_type == "TGIRDER":
        offsets = {
            "bs": 1, "bm": 2, "bc": 3,
            "tt1": 4, "tt2": 5, "x": 6, "tw": 7, "bh": 8, "hh": 9, "yh": 10,
        }
    elif sec_type == "SMALLBOX":
        offsets = {
            "bs": 1, "bm": 2, "bc": 3, "bb": 4,
            "tt": 5, "tb": 6, "tw": 7,
            "xi1": 12, "tt1": 13, "xi2": 14, "yi2": 15,
        }
    elif sec_type == "HOLLOWSLAB":
        offsets = {
            "bs": 1, "bm": 2, "bj": 3,
            "tt": 4, "tb": 5, "tw": 6, "bc": 9,
            "xi1": 10, "yi1": 11, "xi2": 12, "yi2": 13,
        }
    else:
        offsets = {}

    for key, off in offsets.items():
        geo[key] = _arg_float(args, i + off)
        if geo[key] is None:
            geo[key] = _kw_float(node, key)
    if sec_type in ("TGIRDER", "SMALLBOX", "HOLLOWSLAB"):
        if web_t_val is None:
            web_t_val = geo["tw"]
        if tb_val is None and geo["tb"] is not None:
            tb_val = geo["tb"]
    if tt_val is not None and geo["tt"] is None:
        geo["tt"] = tt_val
    # **geo 展开会覆盖前面的 "tb",CONVENTIONALBOX 的 tb_val 须回填 geo
    if tb_val is not None and geo["tb"] is None:
        geo["tb"] = tb_val

    if name is None and h_val is None:
        return None
    return {
        "no": no_val,
        "name": name,
        "type": sec_type,
        "girder_pos": girder_pos,
        "h": h_val,
        "tb": tb_val,
        "web_t": web_t_val,
        "tc_l": tc_l_val,
        "tc_r": tc_r_val,
        "bt_l": bt_l, "bt_r": bt_r, "bb_l": bb_l, "bb_r": bb_r,
        "tw2": tw2_val, "bc_l": bc_l_val, "bc_r": bc_r_val,
        "box_chamfers": box_chamfers,
        **geo,
    }


def _is_main_girder(sec: dict[str, Any]) -> bool:
    """识别主梁截面(参与 H/T 评分),排除桥墩等非主梁截面。

    用截面 **类型** 判断更可靠:RECT = 桥墩/矩形,排除;
    CONVENTIONALBOX / TGIRDER / SMALLBOX / HOLLOWSLAB 都是主梁。
    名字里带「墩」不能直接排除 —— 悬浇梁的「1号墩零号段截面」是主梁 0 号块,
    只是建在墩顶,名字含「墩」但仍是主梁箱梁。
    """
    t = (sec.get("type") or "").upper()
    if t == "RECT":
        return False
    nm = sec.get("name") or ""
    if nm == "桥墩":
        return False
    return True


def _tgirder_role(name: str | None) -> str:
    """按截面名区分跨中标准段 / 支点加厚段 / 过渡段。"""
    nm = name or ""
    if any(k in nm for k in ("标准", "跨中")):
        return "mid"
    if any(k in nm for k in ("墩顶", "加厚", "支点", "端部")):
        return "support"
    return "other"


def _pick_girder_pair(
    sections: list[dict[str, Any]],
    sec_type: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """从指定类型主梁截面中挑选(跨中标准段, 支点加厚段)。

    优先按名称;否则跨中取 tw 最小,支点取 tw 最大(且须大于跨中)。
    """
    want = sec_type.upper()
    t_secs = [s for s in sections if (s.get("type") or "").upper() == want]
    if not t_secs:
        return None, None

    mids = [s for s in t_secs if _tgirder_role(s.get("name")) == "mid"]
    supports = [s for s in t_secs if _tgirder_role(s.get("name")) == "support"]

    mid = mids[0] if mids else None
    if mid is None:
        with_tw = [s for s in t_secs if s.get("tw") is not None]
        mid = min(with_tw, key=lambda s: s["tw"]) if with_tw else t_secs[0]

    support = None
    if supports:
        support = next((s for s in supports if "墩顶" in (s.get("name") or "")), supports[0])
    else:
        mid_tw = mid.get("tw")
        with_tw = [s for s in t_secs if s.get("tw") is not None and s is not mid]
        if mid_tw is not None and with_tw:
            cand = max(with_tw, key=lambda s: s["tw"])
            if cand["tw"] > mid_tw + 1e-9:
                support = cand

    return mid, support


def _pick_t_girder_pair(
    sections: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """兼容旧名:TGIRDER 跨中/支点对。"""
    return _pick_girder_pair(sections, "TGIRDER")


def _scan_sections(tree: ast.AST) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_section_call(node):
            params = _extract_section(node)
            if params:
                out.append(params)
    return out


# ---- 节点 ----

def _is_node_create(node: ast.Call) -> bool:
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    base = ast.unparse(func.value) if hasattr(ast, "unparse") else None
    return base == "engine.node" and func.attr == "create"


def _node_x_index(call: ast.Call) -> int:
    """x 在 args 中的位置(新 API no,x,y,z → 1;旧 API x,y,z,no= → 0)。"""
    has_no_kwarg = any(isinstance(kw, ast.keyword) and kw.arg == "no" for kw in call.keywords)
    return 0 if has_no_kwarg else 1


def _node_x_y_z(call: ast.Call) -> tuple[float | None, float | None, float | None]:
    """提取一个 node.create 的 (x, y, z)。"""
    xi = _node_x_index(call)
    args = call.args
    if len(args) < xi + 1:
        return None, None, None
    x = _const_value(args[xi])
    y = _const_value(args[xi + 1]) if len(args) > xi + 1 else None
    z = _const_value(args[xi + 2]) if len(args) > xi + 2 else None
    x = float(x) if isinstance(x, (int, float)) else None
    y = float(y) if isinstance(y, (int, float)) else None
    z = float(z) if isinstance(z, (int, float)) else None
    return x, y, z


def _merge_xs(xs: list[float], tol: float = 0.5) -> list[float]:
    """x 排序后按容差合并(同一支点左右肢 / 密节点)。"""
    if not xs:
        return []
    ordered = sorted(xs)
    merged = [ordered[0]]
    for x in ordered[1:]:
        if x - merged[-1] > tol:
            merged.append(x)
    return merged


def _cluster_centers(xs: list[float], tol: float) -> list[float]:
    """按容差聚类并取每簇中心(双肢墩两肢 → 一个墩位桩号)。"""
    if not xs:
        return []
    clusters: list[list[float]] = []
    for x in sorted(xs):
        if clusters and x - clusters[-1][-1] <= tol:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    return [round(sum(c) / len(c), 3) for c in clusters]


def _span_lengths_from_xs(xs: list[float], min_span: float = 1.0) -> list[float]:
    """相邻支点间距;滤掉 < min_span 的构造缝。"""
    merged = _merge_xs(xs)
    return [round(b - a, 3) for a, b in zip(merged, merged[1:]) if b - a > min_span]


def _cluster_centers(xs: list[float], tol: float) -> list[float]:
    """x 按容差聚类,每簇取形心(双肢墩两肢 → 墩中心桩号)。"""
    if not xs:
        return []
    clusters: list[list[float]] = [[]]
    for x in sorted(xs):
        if clusters[-1] and x - clusters[-1][-1] > tol:
            clusters.append([])
        clusters[-1].append(x)
    return [round(sum(c) / len(c), 3) for c in clusters if c]


def _support_xs(tree: ast.AST) -> list[float]:
    """支座 / 桥墩外节点(y 或 z != 0)的 x,排序去重(0.5m 容差合并)。"""
    xs: list[float] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_node_create(node):
            continue
        _, y, z = _node_x_y_z(node)
        if (y is not None and abs(y) > 0.001) or (z is not None and abs(z) > 0.001):
            x, _, _ = _node_x_y_z(node)
            if x is not None:
                xs.append(x)
    return _merge_xs(xs)


# ---- 通用调用计数 ----

_MATERIAL_CALL = re.compile(r"material\.create\(([^)]*)\)", re.IGNORECASE)
_CONC_GRADE = re.compile(r'"C(\d{2})"')


def _scan_concrete_grade(files: dict[str, str]) -> int | None:
    """主梁混凝土等级(启发式):材料定义中 CONC 类型的最大 C 等级。

    模板常含多种混凝土(如主梁 C55 + 桥墩 C45),主梁一般取最高等级。
    """
    grades: list[int] = []
    for path, text in files.items():
        if "material" not in path and "_3_" not in path:
            continue
        for m in _MATERIAL_CALL.finditer(text):
            args = m.group(1)
            if '"CONC"' not in args.upper():
                continue
            grades.extend(int(g) for g in _CONC_GRADE.findall(args))
    return max(grades) if grades else None

def _count_manager_create(tree: ast.AST | None, manager: str) -> int:
    """数 engine.<manager>.create(...) 出现次数(如 element / boundary / stage / loadcase)。"""
    if tree is None:
        return 0
    n = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            f = node.func
            base = ast.unparse(f.value) if isinstance(f.value, ast.Attribute) and hasattr(ast, "unparse") else None
            if base == f"engine.{manager}" and f.attr == "create":
                n += 1
    return n


_STAGE_CREATE = re.compile(r"\bstage\.create\(")
_ELEM_RANGE = re.compile(r"^(\d+)\s*to\s*(\d+)$", re.IGNORECASE)


def _count_stages(text: str) -> int:
    return len(_STAGE_CREATE.findall(text or ""))


def _expand_elem_spec(spec: Any) -> list[int]:
    """展开单元编号参数:3 / '3' / '1to4' → [3] / [1,2,3,4]。"""
    if isinstance(spec, bool):
        return []
    if isinstance(spec, int):
        return [spec]
    if isinstance(spec, float) and spec.is_integer():
        return [int(spec)]
    if isinstance(spec, str):
        s = spec.strip()
        m = _ELEM_RANGE.fullmatch(s)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            lo, hi = (a, b) if a <= b else (b, a)
            return list(range(lo, hi + 1))
        if s.isdigit():
            return [int(s)]
    return []


def _is_boundary_node_assign(call: ast.Call) -> bool:
    """engine.boundary.get(n).assign(...) — 不是 boundary.group.create(..., 'a', ...)。"""
    func = call.func
    if not isinstance(func, ast.Attribute) or func.attr != "assign":
        return False
    get_call = func.value
    if not isinstance(get_call, ast.Call):
        return False
    get_func = get_call.func
    if not isinstance(get_func, ast.Attribute) or get_func.attr != "get":
        return False
    try:
        base = ast.unparse(get_func.value)
    except Exception:
        return False
    return base == "engine.boundary"


def _scan_boundary_support_nodes(
    bnd_tree: ast.AST | None,
    nodes: dict[int, tuple[float, float, float]],
) -> list[int]:
    """从 boundary.get(n).assign 收集**点支承**节点号(单跨简支常无偏轴墩节点)。

    整跨批量约束(支架现浇的 "1to39" 之类)不是支座,按数量剔除。
    """
    if bnd_tree is None or not nodes:
        return []
    bulk_limit = max(8, len(nodes) // 4)
    out: set[int] = set()
    for node in ast.walk(bnd_tree):
        if not isinstance(node, ast.Call) or not _is_boundary_node_assign(node):
            continue
        for arg in node.args[1:]:
            ids = [n for n in _expand_elem_spec(_const_value(arg)) if n in nodes]
            if not ids or len(ids) > bulk_limit:
                continue
            out.update(ids)
    return sorted(out)


def _is_plan_curved(nodes: dict[int, tuple[float, float, float]]) -> bool:
    """平面弯桥判定:多数节点偏离 y=0 轴 → x 不再是桩号,且 y 偏移不代表支座。"""
    if not nodes:
        return False
    off = sum(1 for _, y, _ in nodes.values() if abs(y) > 0.5)
    return off * 2 > len(nodes)


def _girder_chainage(
    nodes: dict[int, tuple[float, float, float]],
    beams: list[dict[str, Any]],
    girder_sec_nos: set[int],
) -> tuple[dict[int, float], float]:
    """沿主梁单元链累计弧长,返回 (节点号 → 桩号, 主梁弧长)。

    弯桥的 x 不是桩号,需按单元连接顺序累加空间距离;桥墩单元不入链。
    """
    adj: dict[int, list[tuple[int, float]]] = {}
    for b in beams:
        if girder_sec_nos and (
            b["nSec1"] not in girder_sec_nos or b["nSec2"] not in girder_sec_nos
        ):
            continue
        n1, n2 = nodes.get(b["node1"]), nodes.get(b["node2"])
        if not n1 or not n2:
            continue
        length = (
            (n1[0] - n2[0]) ** 2 + (n1[1] - n2[1]) ** 2 + (n1[2] - n2[2]) ** 2
        ) ** 0.5
        if length <= 1e-12:
            continue
        adj.setdefault(b["node1"], []).append((b["node2"], length))
        adj.setdefault(b["node2"], []).append((b["node1"], length))
    if not adj:
        return {}, 0.0

    ends = [n for n, nb in adj.items() if len(nb) == 1]
    start = min(ends) if ends else min(adj)
    chainage = {start: 0.0}
    stack = [start]
    while stack:
        cur = stack.pop()
        for nxt, length in adj[cur]:
            if nxt not in chainage:
                chainage[nxt] = chainage[cur] + length
                stack.append(nxt)
    return chainage, max(chainage.values())


_PIER_LEG_TOL = 10.0   # m: 同一墩双肢的最大肢距(小于此视作一个墩位)
_END_INSET_TOL = 1.0   # m: 端支座相对梁端的内缩量上限


def _design_spans_from_geometry(
    axis_xs: list[float],
    support_xs: list[float],
) -> tuple[list[float], float | None]:
    """按设计桩号还原各跨跨径与联长。返回 (spans, 联长)。

    模型习惯把桥梁起点放在 x=0,首节点留半条梁缝(x≈0.04~0.12),
    故联长 = max_x + min_x,而梁长(max-min)比标准跨径小一条缝。
    中间支点(桥墩)桩号即累计跨径;端支座相对梁端内缩,不作为跨径分界。
    双肢墩的两肢按 10 m 容差并成一个墩位。
    """
    if not axis_xs:
        return [], None
    x0, x1 = min(axis_xs), max(axis_xs)
    if 0.0 < x0 < _END_INSET_TOL:
        origin, end = 0.0, x1 + x0
    else:
        origin, end = x0, x1
    if end - origin <= 1.0:
        return [], None

    interior = [
        x for x in support_xs
        if x - x0 > _END_INSET_TOL and x1 - x > _END_INSET_TOL
    ]
    stations = [origin, *_cluster_centers(interior, _PIER_LEG_TOL), end]
    spans = [round(b - a, 3) for a, b in zip(stations, stations[1:]) if b - a > 1.0]
    return spans, round(end - origin, 3)


def _main_span_from_nodes(
    design_spans: list[float],
    total_length: float | None,
    *,
    main_span_from_piers: float | None = None,
) -> float | None:
    """主跨 L:设计跨径中的最大跨。不读目录名。

    优先取刚构识别出的墩间距(有 z 向墩高校验),其次取设计跨径最大值,
    最后退回全联总长(单跨且支座信息缺失时)。
    """
    if main_span_from_piers is not None and float(main_span_from_piers) > 1.0:
        return round(float(main_span_from_piers), 3)
    if design_spans:
        return max(design_spans)
    if total_length is not None and float(total_length) > 1.0:
        return round(float(total_length), 3)
    return None


def _is_prop_assign_thickness(node: ast.Call) -> bool:
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr != "assign_component_thickness":
        return False
    base = ast.unparse(func.value) if hasattr(ast, "unparse") else None
    return base == "engine.prop"


def _scan_component_thickness_avg(tree: ast.AST | None) -> float | None:
    """从 assign_component_thickness 按单元数求平均(模型自重/构件厚度字段)。

    **注意**:这不是文档口径的混凝土折算厚度(砼方/桥面面积)。
    T 梁折算厚度应使用 section_area_avg / beam_width。
    同一单元多次赋值时后者覆盖前者。
    """
    if tree is None:
        return None
    elem_thk: dict[int, float] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_prop_assign_thickness(node):
            continue
        args = node.args
        if len(args) < 3:
            continue
        thk = _const_value(args[0])
        if not isinstance(thk, (int, float)) or isinstance(thk, bool):
            continue
        thk_f = float(thk)
        # args[1] 为 op('a'/'s'/'r');其后为单元
        for spec_node in args[2:]:
            spec = _const_value(spec_node)
            for eno in _expand_elem_spec(spec):
                elem_thk[eno] = thk_f
    if not elem_thk:
        return None
    return sum(elem_thk.values()) / len(elem_thk)


def _is_stage_create(node: ast.Call) -> bool:
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr != "create":
        return False
    base = ast.unparse(func.value) if hasattr(ast, "unparse") else None
    return base == "engine.stage"


def _scan_stage_names(tree: ast.AST | None, text: str = "") -> list[str]:
    """提取 stage.create 的阶段名。"""
    names: list[str] = []
    if tree is not None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not _is_stage_create(node):
                continue
            # create(no, name, duration) 或 create(name=..., ...)
            name_v = _kw_str(node, "name")
            if name_v is None and len(node.args) >= 2:
                v = _const_value(node.args[1])
                if isinstance(v, str):
                    name_v = v
            if name_v is None and len(node.args) >= 1:
                # 旧式 create(name, duration) 无 no
                v0 = _const_value(node.args[0])
                if isinstance(v0, str):
                    name_v = v0
            if name_v:
                names.append(name_v)
    if names:
        return names
    # 文本兜底
    for m in re.finditer(
        r"stage\.create\s*\(\s*[^,]+,\s*[\"']([^\"']+)[\"']",
        text or "",
    ):
        names.append(m.group(1))
    return names


def _beam_width_from_section(sec: dict[str, Any] | None) -> float | None:
    """单片梁宽/梁间距代理。

    TGIRDER / SMALLBOX: 2*bm + 2*bc
    HOLLOWSLAB: bs(单片板宽)
    """
    if not sec:
        return None
    st = (sec.get("type") or "").upper()
    if st == "HOLLOWSLAB":
        bs = sec.get("bs")
        return float(bs) if bs is not None else None
    bm = sec.get("bm")
    if bm is None:
        return None
    bc = sec.get("bc") or 0.0
    return 2.0 * float(bm) + 2.0 * float(bc)


def _beam_width_from_tgirder(sec: dict[str, Any] | None) -> float | None:
    """兼容旧名。"""
    return _beam_width_from_section(sec)


def _tgirder_flange_width(sec: dict[str, Any]) -> float | None:
    """TGIRDER 顶板总宽(Y 向)。

    Middle: 2·(bm+bc); Left/Right: bs+bm+2·bc。
    """
    bs = sec.get("bs")
    bm = sec.get("bm")
    bc = float(sec.get("bc") or 0.0)
    pos = (sec.get("girder_pos") or "Middle").lower()
    if pos in ("left", "right"):
        if bs is None or bm is None:
            return None
        return float(bs) + float(bm) + 2.0 * bc
    if bm is not None:
        return 2.0 * float(bm) + 2.0 * bc
    if bs is not None:
        return 2.0 * float(bs)
    return None


def _tgirder_section_area(sec: dict[str, Any] | None) -> float | None:
    """估算单片 TGIRDER 的 Y–Z 截面面积(m²)。

    分解为:翼缘(含梗斜) + 腹板净高段 + 马蹄(可含倒角梯形)。
    矮 T(bh≈tw)时马蹄不外扩,底部按腹板宽延伸。
    """
    if not sec or (sec.get("type") or "").upper() != "TGIRDER":
        return None
    h, tw = sec.get("h"), sec.get("tw")
    tt1, tt2 = sec.get("tt1"), sec.get("tt2")
    if None in (h, tw, tt1, tt2):
        return None
    bf = _tgirder_flange_width(sec)
    if bf is None or bf <= 0:
        return None

    h = float(h)
    tw = float(tw)
    tt1 = float(tt1)
    tt2 = float(tt2)
    bh = float(sec["bh"]) if sec.get("bh") is not None else tw
    hh = float(sec["hh"]) if sec.get("hh") is not None else 0.0
    x = float(sec["x"]) if sec.get("x") is not None else 0.0
    yh = float(sec["yh"]) if sec.get("yh") is not None else 0.0

    hh = max(0.0, min(hh, max(0.0, h - tt2)))
    # 翼缘:端部厚矩形 + 两侧梗斜三角(倒角宽 x)
    if x > 0.0 and tt2 > tt1:
        a_flange = bf * tt1 + x * (tt2 - tt1)
    else:
        a_flange = bf * tt1 + max(0.0, bf - tw) * max(0.0, tt2 - tt1) / 2.0

    h_web = max(0.0, h - tt2 - hh)
    a_web = tw * h_web

    if bh <= tw + 0.02 + 1e-9:
        a_hoof = bh * hh
    else:
        yh_eff = min(max(yh, 0.0), hh)
        if yh_eff > 1e-12 and hh > yh_eff + 1e-12:
            a_hoof = bh * (hh - yh_eff) + 0.5 * (bh + tw) * yh_eff
        elif hh > 1e-12:
            a_hoof = 0.5 * (bh + tw) * hh
        else:
            a_hoof = 0.0

    return a_flange + a_web + a_hoof


def _box_section_area(sec: dict[str, Any] | None) -> float | None:
    """估算单室 CONVENTIONALBOX 的 Y–Z 截面面积(m²)。

    箱室顶板 + 悬臂翼缘(根部 Tt 渐薄至端部 Tc,按梯形) + 底板 + 腹板 + 倒角三角。
    """
    if not sec or (sec.get("type") or "").upper() not in ("CONVENTIONALBOX", "CONVENTIONAL"):
        return None
    vals = (sec.get("h"), sec.get("tt"), sec.get("tb"),
            sec.get("bt_l"), sec.get("bt_r"), sec.get("bb_l"), sec.get("bb_r"))
    if any(v is None for v in vals):
        return None
    h, tt, tb, bt_l, bt_r, bb_l, bb_r = (float(v) for v in vals)
    tw1 = sec.get("web_t")
    tw2 = sec.get("tw2") if sec.get("tw2") is not None else tw1
    if tw1 is None or tw2 is None:
        return None
    bc_l = float(sec.get("bc_l") or 0.0)
    bc_r = float(sec.get("bc_r") or 0.0)
    tc_vals = [float(v) for v in (sec.get("tc_l"), sec.get("tc_r")) if v is not None]
    tc = sum(tc_vals) / len(tc_vals) if tc_vals else tt
    a_top = max(0.0, bt_l + bt_r - bc_l - bc_r) * tt + (bc_l + bc_r) * (tt + tc) / 2.0
    a_bot = (bb_l + bb_r) * tb
    a_web = (float(tw1) + float(tw2)) * max(0.0, h - tt - tb)
    a_ch = sum(0.5 * w * hh for w, hh in sec.get("box_chamfers") or [])
    return a_top + a_bot + a_web + a_ch


def _smallbox_section_area(sec: dict[str, Any] | None) -> float | None:
    """估算单室 SMALLBOX 的 Y–Z 截面面积(m²)。

    顶板(主箱 + 两侧悬臂) + 底板 + 两片腹板。梗腋 xi1/xi2 已在截面建模中,
    此处用简化矩形分解,误差在梗腋面积量级,对混凝土折算厚度影响 ≤5%。
    """
    if not sec or (sec.get("type") or "").upper() != "SMALLBOX":
        return None
    h, tt, tb, tw, bm = sec.get("h"), sec.get("tt"), sec.get("tb"), sec.get("tw"), sec.get("bm")
    if None in (h, tt, tb, tw, bm):
        return None
    h, tt, tb, tw, bm = float(h), float(tt), float(tb), float(tw), float(bm)
    bc = float(sec.get("bc") or 0.0)
    box_w = 2.0 * bm  # 主箱宽(顶/底)
    a_top = (box_w + 2 * bc) * tt
    a_bot = box_w * tb
    a_web = 2.0 * tw * max(0.0, h - tt - tb)
    return a_top + a_bot + a_web


def _hollowslab_section_area(sec: dict[str, Any] | None) -> float | None:
    """估算单片 HOLLOWSLAB 的 Y–Z 截面面积(m²)。

    用外轮廓矩形扣除空心部分:A = bs·h·(1 - 空心率)。
    空心率取跨中截面(同 D4 评分口径)。
    """
    if not sec or (sec.get("type") or "").upper() != "HOLLOWSLAB":
        return None
    h, bs = sec.get("h"), sec.get("bs")
    if h is None or bs is None:
        return None
    void = _hollow_void_ratio(sec)
    if void is None:
        return None
    return float(bs) * float(h) * (1.0 - float(void))


def _girder_section_area(sec: dict[str, Any], sec_type: str) -> float | None:
    if sec_type == "TGIRDER":
        return _tgirder_section_area(sec)
    if sec_type in ("CONVENTIONALBOX", "CONVENTIONAL"):
        return _box_section_area(sec)
    if sec_type == "SMALLBOX":
        return _smallbox_section_area(sec)
    if sec_type == "HOLLOWSLAB":
        return _hollowslab_section_area(sec)
    return None


def _avg_girder_section_area(
    sections: list[dict[str, Any]],
    nodes: dict[int, tuple[float, float, float]],
    beams: list[dict[str, Any]],
    sec_type: str = "TGIRDER",
) -> float | None:
    """按梁单元长度加权的平均截面面积(m² = m³/m)。

    单元贡献: 0.5·(A1+A2)·L; A_avg = Σ(A·L) / ΣL。
    无梁单元时退回各截面面积简单平均。
    """
    want = sec_type.upper()
    by_no: dict[int, dict[str, Any]] = {}
    areas_fallback: list[float] = []
    for s in sections:
        if (s.get("type") or "").upper() != want:
            continue
        a = _girder_section_area(s, want)
        if a is None:
            continue
        areas_fallback.append(a)
        no = s.get("no")
        if isinstance(no, int):
            by_no[no] = s

    total_al = 0.0
    total_l = 0.0
    for b in beams:
        s1 = by_no.get(b["nSec1"])
        s2 = by_no.get(b["nSec2"])
        if not s1 or not s2:
            continue
        a1 = _girder_section_area(s1, want)
        a2 = _girder_section_area(s2, want)
        if a1 is None or a2 is None:
            continue
        n1 = nodes.get(b["node1"])
        n2 = nodes.get(b["node2"])
        if not n1 or not n2:
            continue
        dx = n1[0] - n2[0]
        dy = n1[1] - n2[1]
        dz = n1[2] - n2[2]
        length = (dx * dx + dy * dy + dz * dz) ** 0.5
        if length <= 1e-12:
            continue
        total_al += 0.5 * (a1 + a2) * length
        total_l += length

    if total_l > 1e-12:
        return total_al / total_l
    if areas_fallback:
        return sum(areas_fallback) / len(areas_fallback)
    return None


def _hollow_void_ratio(sec: dict[str, Any] | None) -> float | None:
    """空心板空心率近似:矩形孔洞 / 外轮廓矩形。

    void ≈ (bs - 2·tw) · (h - tt - tb) / (bs · h)
    """
    if not sec:
        return None
    h, bs, tw = sec.get("h"), sec.get("bs"), sec.get("tw")
    tt, tb = sec.get("tt"), sec.get("tb")
    if None in (h, bs, tw, tt, tb) or h <= 0 or bs <= 0:
        return None
    inner_w = float(bs) - 2.0 * float(tw)
    inner_h = float(h) - float(tt) - float(tb)
    if inner_w <= 0 or inner_h <= 0:
        return 0.0
    return (inner_w * inner_h) / (float(bs) * float(h))


# ---- 节点 / 单元 / 梁高纵向分布(变截面检查用)----

def _scan_nodes_full(tree: ast.AST | None) -> dict[int, tuple[float, float, float]]:
    """从 _5_node.py 抓所有节点,返 {no: (x, y, z)}。

    新 API:engine.node.create(no, x, y, z)。旧 API(x,y,z,no=)由 _node_x_index 处理。
    """
    if tree is None:
        return {}
    out: dict[int, tuple[float, float, float]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_node_create(node):
            continue
        # no 在 args[0](新 API)或 keywords(旧 API)
        no_v: int | None = None
        if node.args:
            v0 = _const_value(node.args[0])
            if isinstance(v0, int):
                no_v = v0
        if no_v is None:
            for kw in node.keywords:
                if kw.arg == "no":
                    v = _const_value(kw.value)
                    if isinstance(v, int):
                        no_v = v
                    break
        if no_v is None:
            continue
        x, y, z = _node_x_y_z(node)
        out[no_v] = (x or 0.0, y or 0.0, z or 0.0)
    return out


def _scan_beams(tree: ast.AST | None) -> list[dict[str, Any]]:
    """从 _6_element.py 抓所有 BEAM3D 单元。

    返 [{no, node1, node2, nSec1, nSec2}, ...]。
    签名:engine.element.create(no, "BEAM3D", node1, node2, nMat, nSec1, nSec2, ...)
    """
    if tree is None:
        return []
    out: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        base = ast.unparse(func.value) if hasattr(ast, "unparse") else None
        if base != "engine.element" or func.attr != "create":
            continue
        args = node.args
        if len(args) < 7:
            continue
        type_v = _const_value(args[1])
        if type_v != "BEAM3D":
            continue
        no = _const_value(args[0])
        n1 = _const_value(args[2])
        n2 = _const_value(args[3])
        ns1 = _const_value(args[5])
        ns2 = _const_value(args[6])
        if not all(isinstance(x, int) for x in (no, n1, n2, ns1, ns2)):
            continue
        out.append({"no": no, "node1": n1, "node2": n2, "nSec1": ns1, "nSec2": ns2})
    return out


def _build_height_profile(
    sections: list[dict[str, Any]],
    nodes: dict[int, tuple[float, float, float]],
    beams: list[dict[str, Any]],
) -> list[tuple[float, float]]:
    """联合 _4/_5/_6 抽 [(x, h), ...] 按 x 升序。

    截面高定义在单元两端节点上(nSec1@node1, nSec2@node2),故采端点而非单元中点。
    若误用 (x_mid, h(nSec1)),变截面段会把 i 端梁高错挂到跨中,n_H 系统性偏低
    (如设计 1.8 被拟成 ~1.45)。平直段(两端同高)仍会进入剖面,由 D3 匹配阶段
    识别为根部/跨中等截面平台后剔除,只对变化段拟合。

    同 x 多值取平均。过滤 h 为 None 的截面。
    """
    sec_by_no: dict[int, dict[str, Any]] = {
        s["no"]: s for s in sections if s.get("no") is not None
    }
    by_x: dict[float, list[float]] = {}
    for b in beams:
        n1 = nodes.get(b["node1"])
        n2 = nodes.get(b["node2"])
        if n1 is None or n2 is None:
            continue
        for node_xyz, sec_no in ((n1, b["nSec1"]), (n2, b["nSec2"])):
            sec = sec_by_no.get(sec_no)
            if sec is None or sec.get("h") is None:
                continue
            x_key = round(float(node_xyz[0]), 4)
            by_x.setdefault(x_key, []).append(float(sec["h"]))
    out = sorted(
        ((x, sum(hs) / len(hs)) for x, hs in by_x.items()),
        key=lambda p: p[0],
    )
    return out


def _girder_total_length(
    girder_sections: list[dict[str, Any]],
    nodes: dict[int, tuple[float, float, float]],
    beams: list[dict[str, Any]],
) -> float:
    """主梁单元总长(m):只累计两端截面均为主梁截面的梁单元。

    竖直桥墩/中横梁等 RECT 截面单元不计——否则刚构的"梁总长"虚增,
    每延米钢束用量(kg/m)被稀释约 12%。
    """
    girder_nos = {s["no"] for s in girder_sections if s.get("no") is not None}
    total = 0.0
    for b in beams:
        if b["nSec1"] not in girder_nos or b["nSec2"] not in girder_nos:
            continue
        n1 = nodes.get(b["node1"])
        n2 = nodes.get(b["node2"])
        if not n1 or not n2:
            continue
        dx = n1[0] - n2[0]
        dy = n1[1] - n2[1]
        dz = n1[2] - n2[2]
        length = (dx * dx + dy * dy + dz * dz) ** 0.5
        if length > 1e-12:
            total += length
    return total


def _build_thickness_profile(
    sections: list[dict[str, Any]],
    nodes: dict[int, tuple[float, float, float]],
    beams: list[dict[str, Any]],
) -> list[tuple[float, float]]:
    """联合 _4/_5/_6 抽 [(x, tb), ...] 按 x 升序(端点采样,同 height_profile)。"""
    sec_by_no: dict[int, dict[str, Any]] = {
        s["no"]: s for s in sections if s.get("no") is not None
    }
    by_x: dict[float, list[float]] = {}
    for b in beams:
        n1 = nodes.get(b["node1"])
        n2 = nodes.get(b["node2"])
        if n1 is None or n2 is None:
            continue
        for node_xyz, sec_no in ((n1, b["nSec1"]), (n2, b["nSec2"])):
            sec = sec_by_no.get(sec_no)
            if sec is None or sec.get("tb") is None:
                continue
            x_key = round(float(node_xyz[0]), 4)
            by_x.setdefault(x_key, []).append(float(sec["tb"]))
    out = sorted(
        ((x, sum(hs) / len(hs)) for x, hs in by_x.items()),
        key=lambda p: p[0],
    )
    return out
# ---- 文件 I/O ----

def _read(files: dict[str, str], path: str) -> str:
    return files.get(path, "")


def _parse(files: dict[str, str], path: str) -> ast.AST | None:
    text = _read(files, path)
    if not text:
        return None
    try:
        return ast.parse(text, filename=path)
    except SyntaxError:
        return None
# 关键字 → 桥型(顺序敏感:先匹配更具体的)
_TYPE_KEYWORDS: list[tuple[str, str]] = [
    ("刚构", "rigid_frame"),
    ("悬浇", "cantilever_box"),
    ("T梁", "t_girder"),
    ("T 梁", "t_girder"),
    ("小箱梁", "precast_small_box"),
    ("空心板", "hollow_slab"),
]


def detect_bridge_type(name: str) -> str:
    """[调用方工具] 从目录名识别桥型。evaluate 不调用此函数。"""
    for kw, btype in _TYPE_KEYWORDS:
        if kw in name:
            return btype
    return "unknown"


_SPAN_PLUS = re.compile(r"(\d+(?:\.\d+)?)(?:\+(\d+(?:\.\d+)?))+")
_SPAN_M = re.compile(r"(\d+(?:\.\d+)?)m")


def spans_from_name(name: str) -> list[float] | None:
    """[调用方工具] 从目录名解析跨径列表。evaluate 不调用此函数。

    优先匹配 `35+60+35` / `62.5+115+62.5` 这类 + 分隔的多跨;
    退化匹配 `30m`(排除 `12.75m宽` 这类宽度)。
    """
    m = _SPAN_PLUS.search(name)
    if m:
        # 把整个匹配段(含 +)里的数字全抽出来
        return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", m.group(0))]
    spans: list[float] = []
    for mm in _SPAN_M.finditer(name):
        end = mm.end()
        # 紧跟「宽」字 → 是桥宽不是跨径,跳过
        if end < len(name) and name[end] == "宽":
            continue
        spans.append(float(mm.group(1)))
    return spans if spans else None
# 竖向预应力命名(严格):不含 VerCurve / 单纯 -z 等纵向束常见误伤。
_VERTICAL_NAME_RE = re.compile(
    r"竖向|vertical|(?:^|[^a-z0-9])(?:sv|wv|vps)(?:[^a-z0-9]|$)",
    re.IGNORECASE,
)


def _looks_like_vertical_name(name: str) -> bool:
    """钢束名 / 荷载工况名是否标明竖向预应力。"""
    if not name:
        return False
    lowered = name.lower()
    # ARC2D 的 VerCurve/HorCurve 是纵向束竖弯/平弯投影,不是竖向预应力
    if "vercurve" in lowered or "horcurve" in lowered:
        if "竖向" not in name and "vertical" not in lowered:
            return False
    return _VERTICAL_NAME_RE.search(name) is not None


def _loadcase_texts(files: dict[str, str]) -> list[str]:
    """优先取 prep/_8_loadcase.py;找不到再退回文件名含 loadcase 的文本。"""
    texts: list[str] = []
    for key, text in files.items():
        norm = key.replace("\\", "/")
        if norm.endswith("_8_loadcase.py") or norm.endswith("/_8_loadcase.py"):
            texts.append(text)
    if texts:
        return texts
    for key, text in files.items():
        if "loadcase" in key.replace("\\", "/").lower():
            texts.append(text)
    return texts


def _scan_pst_from_loadcase(tree: ast.AST) -> tuple[set[str], set[str]]:
    """从 _8_loadcase AST 提取 (含 PST 的工况名, 被 PST 张拉的钢束名)。

    只统计真正执行了 create("PST", ...) 的工况,避免空工况名误伤。
    """
    pst_loadcases: set[str] = set()
    pst_tendons: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # engine.load.get(name).create("PST", tendon, ...)
        if not isinstance(func, ast.Attribute) or func.attr != "create":
            continue
        if not isinstance(func.value, ast.Call):
            continue
        get_call = func.value
        if not isinstance(get_call.func, ast.Attribute) or get_call.func.attr != "get":
            continue
        get_base = ast.unparse(get_call.func.value) if hasattr(ast, "unparse") else ""
        if get_base != "engine.load":
            continue
        if len(node.args) < 2:
            continue
        if _const_value(node.args[0]) != "PST":
            continue
        tendon = _const_value(node.args[1])
        if isinstance(tendon, str):
            pst_tendons.add(tendon)
        if get_call.args:
            lc_name = _const_value(get_call.args[0])
            if isinstance(lc_name, str):
                pst_loadcases.add(lc_name)
    return pst_loadcases, pst_tendons


def _has_vertical_from_loadcase(files: dict[str, str]) -> bool:
    """是否通过 _8_loadcase PST + 竖向命名判定为竖向预应力。

    须同时满足「真正张拉」+「竖向命名」:
      1. 存在 load...create("PST", 钢束名, ...)
      2. 且工况名或钢束名匹配严格竖向标记
    不把纵向束 BB*-z / VerCurve 当成竖向预应力。
    """
    texts = _loadcase_texts(files)
    if not texts:
        return False
    for text in texts:
        try:
            tree = ast.parse(text)
        except Exception:
            continue
        pst_loadcases, pst_tendons = _scan_pst_from_loadcase(tree)
        if not pst_tendons:
            continue
        if any(_looks_like_vertical_name(n) for n in pst_loadcases):
            return True
        if any(_looks_like_vertical_name(n) for n in pst_tendons):
            return True
    return False


def _scan_web_vertical_section_nos(tree: ast.AST | None) -> set[int]:
    """从 _4_section 扫描含 WEBVERTICALREBAR(腹板竖筋)的截面编号。

    对应 .out RebarS 行中的 WEBVERTICALREBAR,例如:
      section.get(16).add_rebar_s("WEBVERTICALREBAR", 4, 0.5, area, 90, force, 0.8)
    """
    if tree is None:
        return set()
    out: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # engine.section.get(no).add_rebar_s("WEBVERTICALREBAR", ...)
        if not isinstance(func, ast.Attribute) or func.attr != "add_rebar_s":
            continue
        if not node.args:
            continue
        kind = _const_value(node.args[0])
        if not isinstance(kind, str) or kind.upper() != "WEBVERTICALREBAR":
            continue
        get_call = func.value
        if not isinstance(get_call, ast.Call):
            continue
        if not isinstance(get_call.func, ast.Attribute) or get_call.func.attr != "get":
            continue
        get_base = ast.unparse(get_call.func.value) if hasattr(ast, "unparse") else ""
        if get_base != "engine.section":
            continue
        if not get_call.args:
            continue
        sec_no = _const_value(get_call.args[0])
        if isinstance(sec_no, int):
            out.add(sec_no)
    return out


def _has_web_vertical_near_supports(
    *,
    L: float,
    support_xs: list[float],
    nodes: dict[int, tuple[float, float, float]],
    beams: list[dict[str, Any]],
    web_secs: set[int],
) -> bool:
    """支点两侧各 L/3 范围内,是否有梁单元使用含 WEBVERTICALREBAR 的截面。

    测试说明中「3/L」按工程习惯理解为跨径的三分之一(L/3);剪力高峰常写 L/4。
    """
    if L <= 0 or not support_xs or not web_secs or not beams:
        return False
    half = L / 3.0

    def near_support(x: float) -> bool:
        return any(abs(x - xs) <= half + 1e-9 for xs in support_xs)

    for b in beams:
        if b["nSec1"] not in web_secs and b["nSec2"] not in web_secs:
            continue
        n1 = nodes.get(b["node1"])
        n2 = nodes.get(b["node2"])
        if n1 is None or n2 is None:
            continue
        x1, x2 = float(n1[0]), float(n2[0])
        x_mid = 0.5 * (x1 + x2)
        # 单元中点或任一端落入支点 L/3 带即计
        if near_support(x_mid) or near_support(x1) or near_support(x2):
            return True
    return False


def _has_vertical_tendon(
    files: dict[str, str],
    *,
    L: float | None = None,
    support_xs: list[float] | None = None,
) -> bool:
    """是否设置竖向预应力(悬浇/刚构 D5,L>75 时用)。

    判定(满足其一即可):
      A. _8_loadcase 中 PST + 竖向工况/钢束命名(旧路径,兼容专用竖向束模型)
      B. _4_section 腹板竖筋 WEBVERTICALREBAR,且落在支点两侧各 L/3 的梁段上
         (测试给定的主路径:RebarS 含 WEBVERTICALREBAR)

    无 L/支点时,B 退化:只要截面里出现 WEBVERTICALREBAR 即 True
    (提取阶段占位;评分前会用 L 再算一次)。
    """
    if _has_vertical_from_loadcase(files):
        return True

    sec_tree = _parse(files, "prep/_4_section.py")
    web_secs = _scan_web_vertical_section_nos(sec_tree)
    if not web_secs:
        return False

    if L is None or L <= 0 or not support_xs:
        return True

    node_tree = _parse(files, "prep/_5_node.py")
    elem_tree = _parse(files, "prep/_6_element.py")
    nodes = _scan_nodes_full(node_tree)
    beams = _scan_beams(elem_tree)
    return _has_web_vertical_near_supports(
        L=float(L),
        support_xs=list(support_xs),
        nodes=nodes,
        beams=beams,
        web_secs=web_secs,
    )


def _has_prestress(files: dict[str, str]) -> bool:
    """是否存在纵向/一般预应力张拉——依据 _8_loadcase 中任意 PST。

    用于简支 T 梁区分 PC(预应力)与 RC(普通钢筋混凝土)。
    """
    for text in _loadcase_texts(files):
        try:
            tree = ast.parse(text)
        except Exception:
            continue
        _, pst_tendons = _scan_pst_from_loadcase(tree)
        if pst_tendons:
            return True
    return False


# GB/T 5224 常用钢绞线公称面积 mm²(其余直径按 πd²/4 兜底)
_STRAND_AREA_MM2: dict[float, float] = {
    9.5: 54.8,
    12.7: 98.7,
    12.9: 100.0,
    15.2: 140.0,
    15.7: 150.0,
    17.8: 191.0,
    21.6: 285.0,
}
_STEEL_DENSITY = 7850.0  # kg/m³


def _strand_area_m2(diameter_mm: float) -> float:
    """单根钢绞线公称面积(m²)。"""
    for key, area in _STRAND_AREA_MM2.items():
        if abs(diameter_mm - key) < 0.05:
            return area * 1e-6
    # 未知直径:按圆截面近似
    return 3.141592653589793 * (diameter_mm * 1e-3 / 2.0) ** 2


def _is_tendon_prop_create(node: ast.Call) -> bool:
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr != "create":
        return False
    base = ast.unparse(func.value) if hasattr(ast, "unparse") else ""
    return base == "engine.tendon.prop"


def _is_tendon_shape_create(node: ast.Call) -> bool:
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr != "create":
        return False
    base = ast.unparse(func.value) if hasattr(ast, "unparse") else ""
    return base == "engine.tendon.shape"


def _scan_tendon_props(tree: ast.AST) -> dict[str, dict[str, float]]:
    """解析 tendon.prop.create → {name: {area_m2, n_strands, diameter_mm}}。

    支持后张体内规范输入:
      create(name, "IN", nMat, 1, code, diameter, n_strands, ...)
    以及用户输入面积:
      create(name, "IN", nMat, 0, area_value, ...)
    area_value 约定为整束面积(m²或mm²):≥1e-2 视为 mm²。
    """
    props: dict[str, dict[str, float]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_tendon_prop_create(node):
            continue
        args = node.args
        if len(args) < 5:
            continue
        name = _const_value(args[0])
        if not isinstance(name, str):
            continue
        b_area = _const_value(args[3])
        if b_area == 1 and len(args) >= 7:
            diameter = _const_value(args[5])
            n_strands = _const_value(args[6])
            if not isinstance(diameter, (int, float)) or not isinstance(
                n_strands, (int, float)
            ):
                continue
            d_mm = float(diameter)
            n = float(n_strands)
            props[name] = {
                "diameter_mm": d_mm,
                "n_strands": n,
                "area_m2": _strand_area_m2(d_mm) * n,
            }
        elif b_area == 0 and len(args) >= 5:
            raw = _const_value(args[4])
            if not isinstance(raw, (int, float)):
                continue
            area = float(raw)
            if area >= 1e-2:  # 当作 mm²
                area *= 1e-6
            props[name] = {
                "diameter_mm": 0.0,
                "n_strands": 1.0,
                "area_m2": area,
            }
    return props


def _scan_tendon_shapes(tree: ast.AST) -> dict[str, dict[str, Any]]:
    """解析 tendon.shape.create → {name: {n_num, prop, element_group}}。

    create(name, n_num, prop, element_group, type, curve_name)
    """
    shapes: dict[str, dict[str, Any]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_tendon_shape_create(node):
            continue
        args = node.args
        if len(args) < 3:
            continue
        name = _const_value(args[0])
        n_num = _const_value(args[1])
        prop = _const_value(args[2])
        if not isinstance(name, str) or not isinstance(prop, str):
            continue
        if not isinstance(n_num, (int, float)):
            n_num = 1
        eg = _const_value(args[3]) if len(args) >= 4 else None
        if not isinstance(eg, str):
            eg = _kw_str(node, "element_group") or _kw_str(node, "elemGroup")
        shapes[name] = {
            "n_num": float(n_num),
            "prop": prop,
            "element_group": eg,
        }
    return shapes


def _is_element_group_create(node: ast.Call) -> bool:
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr != "create":
        return False
    base = ast.unparse(func.value) if hasattr(ast, "unparse") else ""
    return base == "engine.element.group"


def _scan_element_groups(tree: ast.AST | None) -> dict[str, set[int]]:
    """按源码顺序解析 element.group.create → {组名: 单元号集合}。

    op: 'c' 清空; 'a' 追加单元规格(如 "1to33")。
    """
    if tree is None:
        return {}
    groups: dict[str, set[int]] = {}

    class _V(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            if _is_element_group_create(node) and node.args:
                gname = _const_value(node.args[0])
                op = _const_value(node.args[1]) if len(node.args) >= 2 else None
                if isinstance(gname, str) and isinstance(op, str):
                    op_l = op.lower()
                    if op_l == "c":
                        groups[gname] = set()
                    elif op_l in ("a", "s", "r"):
                        bucket = groups.setdefault(gname, set())
                        if op_l in ("s", "r"):
                            bucket.clear()
                        for spec_node in node.args[2:]:
                            for eno in _expand_elem_spec(_const_value(spec_node)):
                                bucket.add(eno)
            self.generic_visit(node)

    _V().visit(tree)
    return groups


def _beam_element_lengths(
    nodes: dict[int, tuple[float, float, float]],
    beams: list[dict[str, Any]],
) -> tuple[dict[int, float], float]:
    """单元号 → 长度;并返回梁单元总长。"""
    lengths: dict[int, float] = {}
    total = 0.0
    for b in beams:
        n1 = nodes.get(b["node1"])
        n2 = nodes.get(b["node2"])
        if not n1 or not n2:
            continue
        dx = n1[0] - n2[0]
        dy = n1[1] - n2[1]
        dz = n1[2] - n2[2]
        length = (dx * dx + dy * dy + dz * dz) ** 0.5
        if length <= 1e-12:
            continue
        lengths[int(b["no"])] = length
        total += length
    return lengths, total


def _group_length(
    group_name: str | None,
    groups: dict[str, set[int]],
    elem_lengths: dict[int, float],
) -> float | None:
    """钢束单元组覆盖的梁长;组不存在或空 → None。"""
    if not group_name:
        return None
    ens = groups.get(group_name)
    if not ens:
        return None
    return sum(elem_lengths.get(e, 0.0) for e in ens)


_ZERO_BLOCK_GROUP_RE = re.compile(r"^(?:0号块|零号块)")


def _zero_block_lengths(
    element_groups: dict[str, set[int]],
    nodes_full: dict[int, tuple[float, float, float]],
    beams: list[dict[str, Any]],
) -> list[float]:
    """各主墩 0 号块长度(m)序列,升序。

    取"0号块"单元组(前缀匹配,排除"10号块"等)的元素,按共享节点聚成
    连续段(每墩一段),段长 = 段内节点坐标最大极差。无组或缺几何 → []。
    """
    elem_ids: set[int] = set()
    for gname, ens in element_groups.items():
        if _ZERO_BLOCK_GROUP_RE.match(gname):
            elem_ids |= ens
    ends: dict[int, tuple[int, int]] = {}
    for b in beams:
        eno = int(b["no"])
        if eno in elem_ids:
            ends[eno] = (int(b["node1"]), int(b["node2"]))
    if not ends:
        return []

    parent = {e: e for e in ends}

    def _find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    node_owner: dict[int, int] = {}
    for eno, (n1, n2) in ends.items():
        for n in (n1, n2):
            if n in node_owner:
                ra, rb = _find(eno), _find(node_owner[n])
                if ra != rb:
                    parent[ra] = rb
            else:
                node_owner[n] = eno

    clusters: dict[int, list[int]] = {}
    for eno in ends:
        clusters.setdefault(_find(eno), []).append(eno)

    lens: list[float] = []
    for members in clusters.values():
        pts = [
            nodes_full[n]
            for e in members
            for n in ends[e]
            if n in nodes_full
        ]
        if len(pts) < 2:
            continue
        extent = max(
            ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2) ** 0.5
            for i, p in enumerate(pts)
            for q in pts[i + 1 :]
        )
        if extent > 1e-9:
            lens.append(round(extent, 3))
    return sorted(lens)


def _pst_steel_kg_per_m(
    files: dict[str, str],
    *,
    elem_lengths: dict[int, float] | None = None,
    element_groups: dict[str, set[int]] | None = None,
    girder_length: float | None = None,
) -> float | None:
    """有效预应力钢绞线线密度(kg/m 梁长)。

    有单元组几何时:
      W = Σ n_num·A·7850·L_束,  返回 W / L_全桥
      L_束 取 shape 对应 element_group 覆盖的梁单元长度之和。
    无几何时退回旧口径(假定通长): Σ n_num·A·7850。
    """
    use_len = (
        elem_lengths is not None
        and element_groups is not None
        and girder_length is not None
        and girder_length > 1e-12
    )
    total_kg = 0.0
    total_linear = 0.0
    found = False
    for text in _loadcase_texts(files):
        try:
            tree = ast.parse(text)
        except Exception:
            continue
        _, pst_names = _scan_pst_from_loadcase(tree)
        if not pst_names:
            continue
        props = _scan_tendon_props(tree)
        shapes = _scan_tendon_shapes(tree)
        for tname in pst_names:
            shape = shapes.get(tname)
            if not shape:
                continue
            prop = props.get(shape["prop"])
            if not prop:
                continue
            linear = shape["n_num"] * prop["area_m2"] * _STEEL_DENSITY
            found = True
            if use_len:
                assert elem_lengths is not None
                assert element_groups is not None
                assert girder_length is not None
                L_t = _group_length(
                    shape.get("element_group"), element_groups, elem_lengths,
                )
                if L_t is None:
                    L_t = float(girder_length)  # 组缺失时保守按通长
                total_kg += linear * L_t
            else:
                total_linear += linear
    if not found:
        return None
    if use_len:
        assert girder_length is not None
        return total_kg / float(girder_length)
    return total_linear


def _pst_steel_ratio_kg_m3(
    steel_kg_per_m: float | None,
    section_area_avg: float | None,
) -> float | None:
    """预应力钢绞线用量 kg/m³ = 有效线密度 / 平均截面面积。

    有效线密度已按各束实际长度摊到全桥梁长上,故
    kg/m³ = (Σ n·A·ρ·L_束) / (A_avg · L_全桥)。
    """
    if steel_kg_per_m is None or section_area_avg is None:
        return None
    denom = float(section_area_avg)
    if denom <= 1e-12:
        return None
    return float(steel_kg_per_m) / denom


def _extract_params(files: dict[str, str]) -> dict[str, Any]:
    """从 candidate 代码提取被评价的量。**不**推断桥型。

    主跨 L 从节点/支座几何提取,不读目录名。bridge_type / is_continuous
    由 evaluate 从 resources 注入。
    """
    sec_tree = _parse(files, "prep/_4_section.py")
    node_tree = _parse(files, "prep/_5_node.py")
    stage_text = _read(files, "prep/_10_stage.py")
    stage_tree = _parse(files, "prep/_10_stage.py")
    elem_tree = _parse(files, "prep/_6_element.py")
    bnd_tree = _parse(files, "prep/_7_boundary.py")

    all_sections = _scan_sections(sec_tree) if sec_tree else []
    girder_sections = [s for s in all_sections if _is_main_girder(s) and s["h"] is not None]

    h_values = [s["h"] for s in girder_sections if s["h"] is not None]
    tb_values = [s["tb"] for s in girder_sections if s["tb"] is not None]
    h_mid = min(h_values) if h_values else None
    h_root = max(h_values) if h_values else None
    # T_mid/T_root 配对:与 h 极值同截面
    t_mid = None
    t_root = None
    t_dia_root = None
    t_top_mid = None
    t_top_root = None
    web_t_mid = None
    web_t_support = None
    if h_mid is not None:
        t_mid = next((s["tb"] for s in girder_sections if s["h"] == h_mid and s["tb"] is not None), None)
        t_top_mid = next((s["tt"] for s in girder_sections if s["h"] == h_mid and s["tt"] is not None), None)
        web_t_mid = next((s["web_t"] for s in girder_sections if s["h"] == h_mid and s["web_t"] is not None), None)
    if h_root is not None:
        # 0 号段多片截面共享 h_root，但代表不同纵向位置：
        # 最小底板厚对应支点附近底板渐变拐点，最大底板厚对应支点处横梁。
        root_secs = [s for s in girder_sections if s["h"] == h_root]
        tb_r = [s["tb"] for s in root_secs if s["tb"] is not None]
        t_root = min(tb_r) if tb_r else None
        t_dia_root = max(tb_r) if tb_r else None
        tt_r = [s["tt"] for s in root_secs if s["tt"] is not None]
        t_top_root = max(tt_r) if tt_r else None
        web_r = [s["web_t"] for s in root_secs if s["web_t"] is not None]
        web_t_support = max(web_r) if web_r else None
    if t_mid is None and tb_values:
        t_mid = min(tb_values)
    if t_root is None and tb_values:
        t_root = min(tb_values)
    if t_dia_root is None and tb_values:
        t_dia_root = max(tb_values)
    tt_values = [s["tt"] for s in girder_sections if s["tt"] is not None]
    if t_top_mid is None and tt_values:
        t_top_mid = min(tt_values)
    if t_top_root is None and tt_values:
        t_top_root = max(tt_values)
    # 翼缘端部厚:主梁各截面 TcL/TcR 的均值(通常全桥一致)
    tc_values = [
        v for s in girder_sections for v in (s.get("tc_l"), s.get("tc_r"))
        if v is not None
    ]
    flange_tip = round(sum(tc_values) / len(tc_values), 4) if tc_values else None

    # 变截面检查用:联合 节点 x + 单元两端截面 → [(x, h), ...]
    # 只用主梁截面:刚构墩顶的桥墩/中横梁 RECT 截面(h 非梁高)会污染墩顶桩号,
    # 使根部平台 X_H 误判、n_H 系统性偏低(设计 1.8 被拟成 ~1.55)
    nodes_full = _scan_nodes_full(node_tree)
    beams = _scan_beams(elem_tree)
    height_profile = _build_height_profile(girder_sections, nodes_full, beams)
    thickness_profile = _build_thickness_profile(girder_sections, nodes_full, beams)

    # 剖面法定位根部平台（0 号段）。平台内最小底板厚对应附近渐变拐点，
    # 最大底板厚对应支点处横梁，二者不能混用。
    if height_profile and thickness_profile and h_root is not None:
        h_max = max(h for _, h in height_profile)
        h_min = min(h for _, h in height_profile)
        eps = (h_max - h_min) * 0.005 if h_max > h_min else 0.01
        tb_map = {round(x, 4): tb for x, tb in thickness_profile}
        # 根部平台(0号段):h≈h_max 的连续段
        plateau_xs: set[float] = set()
        for x, h in height_profile:
            if abs(h - h_max) <= eps:
                plateau_xs.add(round(x, 4))
        plateau_tbs = [tb_map[x] for x in plateau_xs if x in tb_map]
        if plateau_tbs:
            t_root = min(plateau_tbs)
            t_dia_root = max(plateau_tbs)

    # 全联总长
    total_length = 0.0
    if nodes_full:
        xs = [x for x, _, _ in nodes_full.values()]
        if xs:
            total_length = max(xs) - min(xs)

    from .bridges.rigid_frame import _extract_rigid_frame_geometry

    rigid_frame_geometry = _extract_rigid_frame_geometry(
        nodes_full, all_sections, beams, elem_tree,
    )

    has_vertical_tendon = _has_vertical_tendon(files)
    has_prestress = _has_prestress(files)

    t_mid_sec, t_support_sec = _pick_girder_pair(girder_sections, "TGIRDER")
    box_mid_sec, box_support_sec = _pick_girder_pair(girder_sections, "SMALLBOX")
    slab_mid_sec, slab_support_sec = _pick_girder_pair(girder_sections, "HOLLOWSLAB")

    # 腹板厚优先用预制梁 tw(按标准/墩顶)
    prefab_mid = t_mid_sec or box_mid_sec or slab_mid_sec
    prefab_support = t_support_sec or box_support_sec or slab_support_sec
    if prefab_mid and prefab_mid.get("tw") is not None:
        web_t_mid = prefab_mid["tw"]
    if prefab_support and prefab_support.get("tw") is not None:
        web_t_support = prefab_support["tw"]

    component_thickness_avg = _scan_component_thickness_avg(elem_tree)
    beam_width = _beam_width_from_section(prefab_mid)
    void_ratio = _hollow_void_ratio(slab_mid_sec)
    stage_names = _scan_stage_names(stage_tree, stage_text)
    girder_types = {(s.get("type") or "").upper() for s in girder_sections}
    area_type = (
        "TGIRDER" if "TGIRDER" in girder_types
        else "CONVENTIONALBOX" if girder_types & {"CONVENTIONALBOX", "CONVENTIONAL"}
        else "SMALLBOX" if "SMALLBOX" in girder_types
        else "HOLLOWSLAB" if "HOLLOWSLAB" in girder_types
        else "TGIRDER"
    )
    section_area_avg = _avg_girder_section_area(
        all_sections, nodes_full, beams, area_type,
    )
    # 文档折算厚度 = 砼方/桥面面积 ≈ A_avg / 梁宽(T梁);
    # 无截面面积时才退回 assign_component_thickness(小箱梁/空心板等)。
    if (
        section_area_avg is not None
        and beam_width is not None
        and float(beam_width) > 1e-12
    ):
        concrete_ratio = float(section_area_avg) / float(beam_width)
    else:
        concrete_ratio = component_thickness_avg
    # 小箱梁/空心板等没有专用面积函数时,用 component_thickness_avg × beam_width 兜底,
    # 让 _pst_steel_ratio_kg_m3 能算 kg/m³
    if section_area_avg is None and beam_width is not None and component_thickness_avg is not None:
        section_area_avg = float(component_thickness_avg) * float(beam_width)
    elem_lengths, _ = _beam_element_lengths(nodes_full, beams)
    girder_length = _girder_total_length(girder_sections, nodes_full, beams)
    element_groups = _scan_element_groups(elem_tree)
    zero_block_lens = _zero_block_lengths(element_groups, nodes_full, beams)
    # 每主墩各一个 0 号块,取偏离 9~14 m 最远(最不利)的一块参与评分
    zero_block_len = (
        max(zero_block_lens, key=lambda x: max(9.0 - x, x - 14.0, 0.0))
        if zero_block_lens
        else None
    )
    pst_steel_kg_per_m = _pst_steel_kg_per_m(
        files,
        elem_lengths=elem_lengths,
        element_groups=element_groups,
        girder_length=girder_length if girder_length > 1e-12 else None,
    )
    pst_steel_ratio = _pst_steel_ratio_kg_m3(
        pst_steel_kg_per_m, section_area_avg,
    )
    curved = _is_plan_curved(nodes_full)
    axis_xs = [x for x, y, z in nodes_full.values() if abs(y) <= 0.5 and abs(z) <= 0.5]
    support_nodes = _scan_boundary_support_nodes(bnd_tree, nodes_full)
    support_xs_out = (
        _support_xs(node_tree) if node_tree is not None and not curved else []
    )
    boundary_xs = _merge_xs([nodes_full[n][0] for n in support_nodes])
    station_xs = support_xs_out if len(support_xs_out) >= 2 else boundary_xs
    if curved:
        # 弯桥:x 不是桩号,按主梁弧长排桩号,支座取边界约束节点
        chainage, girder_arc = _girder_chainage(
            nodes_full, beams, {s["no"] for s in girder_sections if s.get("no") is not None},
        )
        station_xs = _merge_xs([chainage[n] for n in support_nodes if n in chainage])
        span_lengths = _span_lengths_from_xs(station_xs)
        design_total = round(girder_arc, 3) if girder_arc > 1.0 else None
    else:
        span_lengths, design_total = _design_spans_from_geometry(axis_xs, station_xs)
    L_from_nodes = _main_span_from_nodes(
        span_lengths,
        design_total if design_total is not None else total_length,
        main_span_from_piers=rigid_frame_geometry.get("main_span"),
    )

    return {
        # 意图参数(由 evaluate 注入,此处留空)
        "bridge_type": None,
        "L": L_from_nodes,    # 主跨:节点/支座几何,不读目录名
        "is_continuous": None,
        "is_prestressed": None,  # 可选覆盖;默认用 has_prestress 测量
        # 代码测量值
        "H_root": h_root,
        "H_mid": h_mid,
        "T_root": t_root,
        "T_dia_root": t_dia_root,
        "T_mid": t_mid,
        "T_top_mid": t_top_mid,
        "T_top_root": t_top_root,
        "web_t_mid": web_t_mid,
        "web_t_support": web_t_support,
        "flange_tip": flange_tip,
        "t_girder_mid": t_mid_sec,
        "t_girder_support": t_support_sec,
        "small_box_mid": box_mid_sec,
        "small_box_support": box_support_sec,
        "hollow_slab_mid": slab_mid_sec,
        "hollow_slab_support": slab_support_sec,
        "concrete_ratio": (
            None if concrete_ratio is None else round(float(concrete_ratio), 4)
        ),  # 混凝土折算厚度 m³/m² = A_avg/梁宽(T梁) 或 thickness 兜底
        "component_thickness_avg": (
            None
            if component_thickness_avg is None
            else round(float(component_thickness_avg), 4)
        ),  # 模型 assign_component_thickness 均值(非折算厚度)
        "beam_width": beam_width,          # 梁间距/单片梁宽(可被 resources 覆盖)
        "section_area_avg": (
            None if section_area_avg is None else round(section_area_avg, 4)
        ),  # Y–Z 平均截面面积 m²(=m³/m)
        "pst_steel_kg_per_m": (
            None if pst_steel_kg_per_m is None else round(pst_steel_kg_per_m, 4)
        ),
        "pst_steel_ratio": (
            None if pst_steel_ratio is None else round(pst_steel_ratio, 3)
        ),  # 钢绞线 kg/m³ = 线密度 / A_avg
        "void_ratio": void_ratio,          # 空心板空心率近似
        "stage_names": stage_names,
        "total_length": total_length,
        "has_vertical_tendon": has_vertical_tendon,
        "has_prestress": has_prestress,
        "heights": sorted(h_values, reverse=True),
        "thicknesses": sorted(tb_values, reverse=True),
        "thickness_profile": thickness_profile,
        "section_count": len(all_sections),
        "girder_section_count": len(girder_sections),
        "section_types": sorted({s["type"] for s in all_sections if s["type"]}),
        "node_count": _count_manager_create(node_tree, "node"),
        "element_count": _count_manager_create(elem_tree, "element"),
        "boundary_count": _count_manager_create(bnd_tree, "boundary"),
        "stage_count": _count_stages(stage_text) or len(stage_names),
        "support_xs": station_xs or support_xs_out,
        # 变截面曲线拟合用(悬浇梁/刚构)
        "height_profile": height_profile,
        # 连续刚构 D6 用
        "side_spans": rigid_frame_geometry.get("side_spans"),
        "main_span_from_nodes": rigid_frame_geometry.get("main_span"),
        "pier_heights": rigid_frame_geometry.get("pier_heights"),
        "pier_source": rigid_frame_geometry.get("pier_source"),
        # 悬浇连续梁 D5 用:支座间距序列(边中跨比)与主梁混凝土等级
        "span_lengths": span_lengths or None,
        "concrete_grade": _scan_concrete_grade(files),
        # 零号块长度:zero_block_len 为最不利一块;zero_block_lens 为各墩全量
        "zero_block_len": zero_block_len,
        "zero_block_lens": zero_block_lens,
    }
def _rating_of(total: float, max_dim: int = 5) -> str:
    if total >= max_dim:
        return "优秀 / Excellent"
    if total >= max_dim * 0.8:
        return "良好 / Good"
    if total >= max_dim * 0.6:
        return "合格 / Acceptable"
    if total >= max_dim * 0.4:
        return "待改进 / Needs Improvement"
    return "不合格 / Unqualified"


def _assemble(
    params: dict[str, Any],
    dims: list[tuple[str, float, dict[str, Any]]],
    max_dim: int = 1,
    weights: dict[str, float] | None = None,
) -> tuple[float, dict[str, Any]]:
    # 无显式权重时取等权(统一 1 分制,总分 = 各维度均分)
    if weights is None:
        weights = {name: 1.0 / len(dims) for name, _, _ in dims} if dims else {}
    total = sum(w * dict((name, s) for name, s, _ in dims).get(name, 0.0) for name, w in weights.items())
    overall = total / max_dim
    details = {
        "total_score": round(total, 3),
        "max_dim": max_dim,
        "rating": _rating_of(total, max_dim),
        "params": params,
        "dimensions": {name: {"score_5": round(score, 3), **detail} for name, score, detail in dims},
    }
    details["weights"] = dict(weights)
    return overall, details
