# -*- coding: utf-8 -*-
"""悬浇三跨改跨径:只改 _5 节点 x 和 _2 钢束曲线 x。

osis-engine 官方脚本,不是用户自定义插件。无参时把用法打到 stderr 并返回 1。

边跨 ΔL 由边跨现浇段吸收,中跨 ΔL 由合龙两侧恒高段吸收,合龙段 2m 与 T 构刚体平移。
节段对数不同 / 非三跨 / 现浇或恒高段会被拉成负值时拒绝,换同构近邻。

CLI:
  python spanremap.py --to 35+50+35
  python spanremap.py --to 35+50+35 --prep D:\\proj\\py\\prep
  python spanremap.py --to 30+60+30 --from 30+50+30 --dry-run
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

USAGE = """spanremap 用法:

  python spanremap.py --to 35+50+35
  python spanremap.py --to 35+50+35 --prep <工程>/py/prep
  python spanremap.py --to 30+60+30 --from 30+50+30 --dry-run

默认目标=当前 OSIS 工程 get_directory()/py/prep 。只改 _5_node.py / _2_property.py
和 py/项目画像.md 的跨径行;_6~_10 不动。仅支持悬浇三跨、节段方案同构。
"""

PLUS_SPANS = re.compile(
    r"(?<![\d.])(\d+(?:\.\d+)?(?:\s*\+\s*\d+(?:\.\d+)?)+)m?(?![\d.])",
    re.I,
)
NUM_RE = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")
NODE_RE = re.compile(
    r"(engine\.node\.create\(\s*)(\d+)(\s*,\s*)"
    r"([-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?)"
)
ELEM_RE = re.compile(
    r"engine\.element\.create\(\s*(\d+)\s*,\s*\"BEAM3D\"\s*,\s*(\d+)\s*,\s*(\d+)",
)
GROUP_ADD_RE = re.compile(
    r'engine\.element\.group\.create\(\s*"([^"]+)"\s*,\s*"a"\s*,\s*(.*?)\)',
)
GEOM_RE = re.compile(
    r'(engine\.geometry\.create\(\s*"([^"]+)"\s*,\s*"(ARC2D|ARC3D)"\s*,\s*"TENDON"\s*,\s*)(.*?)(\))',
)
SPAN_LINE_RE = re.compile(r"(跨径[:：][^\n]*)")
TOKEN_RE = re.compile(r'"(\d+)\s*to\s*(\d+)"|(\d+)', re.I)

ANCHOR_KEEP = 0.22
MIN_ZONE = 0.3
CLOSURE_TOL = 0.6
EPS = 1e-6


@dataclass
class Node:
    no: int
    x: float
    y: float
    z: float
    line_i: int
    raw_x: str


@dataclass
class Landmarks:
    A: float
    B: float
    C: float
    TLi: float
    midL: float
    midR: float
    TRi: float
    F: float
    G: float
    H: float
    deck_nos: list[int]
    pier_xs: list[float]


@dataclass
class SpanMap:
    old_ks: list[float]
    new_ks: list[float]
    A: float
    H: float
    A_new: float
    H_new: float
    old_spans: list[float]
    new_spans: list[float]
    dL: tuple[float, float, float]

    def piecewise(self, x: float) -> float:
        old, new = self.old_ks, self.new_ks
        if x <= old[0] + EPS:
            return new[0] + (x - old[0])
        if x >= old[-1] - EPS:
            return new[-1] + (x - old[-1])
        for i in range(len(old) - 1):
            a, b = old[i], old[i + 1]
            if x <= b + EPS:
                if b - a < EPS:
                    return new[i]
                t = (x - a) / (b - a)
                return new[i] + t * (new[i + 1] - new[i])
        return new[-1] + (x - old[-1])

    def global_x(self, x: float) -> float:
        if x <= ANCHOR_KEEP:
            return x
        if self.H - x <= ANCHOR_KEEP:
            return self.H_new - (self.H - x)
        return self.piecewise(x)


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconf = getattr(stream, "reconfigure", None)
        if reconf is not None:
            try:
                reconf(encoding="utf-8")
            except Exception:
                pass


def parse_spans(text: str) -> list[float]:
    m = PLUS_SPANS.search(text.replace("＋", "+"))
    if not m:
        return []
    return [float(x.strip()) for x in m.group(1).split("+") if x.strip()]


def format_spans(spans: list[float]) -> str:
    def fmt(x: float) -> str:
        return str(int(x)) if x == int(x) else str(x)

    return "+".join(fmt(x) for x in spans)


def fmt_num(x: float, sample: str) -> str:
    sample = sample.strip()
    if re.search(r"[eE]", sample):
        return f"{x:.6g}"
    dec = 0
    if "." in sample:
        dec = len(sample.split(".", 1)[1])
    if dec == 0:
        if abs(x - round(x)) < 1e-9:
            return str(int(round(x)))
        return f"{x:.6f}".rstrip("0").rstrip(".")
    rounded = round(x, dec)
    return f"{rounded:.{dec}f}"


def expand_tokens(blob: str) -> list[int]:
    out: list[int] = []
    for m in TOKEN_RE.finditer(blob):
        if m.group(1) is not None:
            a, b = int(m.group(1)), int(m.group(2))
            lo, hi = (a, b) if a <= b else (b, a)
            out.extend(range(lo, hi + 1))
        else:
            out.append(int(m.group(3)))
    return out


def parse_nodes(text: str) -> dict[int, Node]:
    nodes: dict[int, Node] = {}
    for i, line in enumerate(text.splitlines()):
        m = NODE_RE.search(line)
        if not m:
            continue
        rest = line[m.end() :]
        nums = NUM_RE.findall(rest)
        if len(nums) < 2:
            continue
        no = int(m.group(2))
        nodes[no] = Node(
            no=no,
            x=float(m.group(4)),
            y=float(nums[0]),
            z=float(nums[1]),
            line_i=i,
            raw_x=m.group(4),
        )
    if not nodes:
        raise RuntimeError("(_5_node.py) 没有解析到 engine.node.create")
    return nodes


def parse_beams_and_groups(text: str) -> tuple[dict[int, tuple[int, int]], dict[str, list[int]]]:
    beams: dict[int, tuple[int, int]] = {}
    for m in ELEM_RE.finditer(text):
        beams[int(m.group(1))] = (int(m.group(2)), int(m.group(3)))
    if not beams:
        raise RuntimeError("(_6_element.py) 没有解析到 BEAM3D")
    groups: dict[str, list[int]] = {}
    for m in GROUP_ADD_RE.finditer(text):
        groups.setdefault(m.group(1), [])
        groups[m.group(1)].extend(expand_tokens(m.group(2)))
    return beams, groups


def _group_elems(groups: dict[str, list[int]], *names: str) -> list[int]:
    for name in names:
        if name in groups and groups[name]:
            return list(dict.fromkeys(groups[name]))
    return []


def _elem_xs(beams: dict[int, tuple[int, int]], nodes: dict[int, Node], eids: list[int]) -> list[float]:
    xs: list[float] = []
    for eid in eids:
        if eid not in beams:
            continue
        n1, n2 = beams[eid]
        xs.append(nodes[n1].x)
        xs.append(nodes[n2].x)
    return xs


def _split_by_x(
    beams: dict[int, tuple[int, int]],
    nodes: dict[int, Node],
    eids: list[int],
    mid: float,
) -> tuple[list[int], list[int]]:
    left, right = [], []
    for eid in eids:
        if eid not in beams:
            continue
        n1, n2 = beams[eid]
        xc = 0.5 * (nodes[n1].x + nodes[n2].x)
        (left if xc < mid else right).append(eid)
    return left, right


def _touch_other(
    beams: dict[int, tuple[int, int]],
    nodes: dict[int, Node],
    boundary: float,
    side: str,
) -> float:
    found: list[float] = []
    for n1, n2 in beams.values():
        xs = (nodes[n1].x, nodes[n2].x)
        for i, x in enumerate(xs):
            if abs(x - boundary) > 1e-4:
                continue
            other = xs[1 - i]
            if side == "left" and other < boundary - 1e-6:
                found.append(other)
            if side == "right" and other > boundary + 1e-6:
                found.append(other)
    if not found:
        raise RuntimeError(f"找不到与合龙边界 x={boundary} 相接的梁单元")
    return max(found) if side == "left" else min(found)


def build_landmarks(
    nodes: dict[int, Node],
    beams: dict[int, tuple[int, int]],
    groups: dict[str, list[int]],
) -> Landmarks:
    deck_nos = sorted({n for pair in beams.values() for n in pair})
    deck_xs = [nodes[n].x for n in deck_nos]
    A, H = min(deck_xs), max(deck_xs)
    mid = 0.5 * (A + H)

    cip = _group_elems(groups, "边跨现浇段")
    if not cip:
        raise RuntimeError("缺少单元组「边跨现浇段」,本插件只支持悬浇三跨模板")
    left_cip, right_cip = _split_by_x(beams, nodes, cip, mid)
    if not left_cip or not right_cip:
        raise RuntimeError("边跨现浇段无法分成左右两段")

    left_cl = _group_elems(groups, "左边跨合龙段")
    right_cl = _group_elems(groups, "右边跨合龙段")
    both_cl = _group_elems(groups, "边跨合龙段")
    if not left_cl or not right_cl:
        l2, r2 = _split_by_x(beams, nodes, both_cl, mid)
        left_cl = left_cl or l2
        right_cl = right_cl or r2
    if not left_cl or not right_cl:
        raise RuntimeError("缺少边跨合龙段(左边跨合龙段/右边跨合龙段)")

    mid_cl = _group_elems(groups, "中跨合龙段", "中跨1合龙段")
    if not mid_cl:
        raise RuntimeError("缺少单元组「中跨合龙段」")

    B = max(_elem_xs(beams, nodes, left_cip))
    C = max(_elem_xs(beams, nodes, left_cl))
    F = min(_elem_xs(beams, nodes, right_cl))
    G = max(_elem_xs(beams, nodes, right_cl))
    mid_xs = _elem_xs(beams, nodes, mid_cl)
    midL, midR = min(mid_xs), max(mid_xs)
    TLi = _touch_other(beams, nodes, midL, "left")
    TRi = _touch_other(beams, nodes, midR, "right")

    for name, lo, hi in (
        ("左边跨合龙", B, C),
        ("中跨合龙", midL, midR),
        ("右边跨合龙", F, G),
    ):
        length = hi - lo
        if abs(length - 2.0) > CLOSURE_TOL:
            raise RuntimeError(f"{name} 长度 {length:.3f}m,期望约 2m,请换同构模板")

    pier_xs = sorted(
        {
            nd.x
            for nd in nodes.values()
            if abs(nd.y) > 0.5 and A + 1.0 < nd.x < H - 1.0
        }
    )
    # 一对左右偏置共用同一 x,去重
    uniq: list[float] = []
    for x in pier_xs:
        if not uniq or abs(x - uniq[-1]) > 0.05:
            uniq.append(x)
    pier_xs = uniq

    return Landmarks(
        A=A, B=B, C=C, TLi=TLi, midL=midL, midR=midR, TRi=TRi, F=F, G=G, H=H,
        deck_nos=deck_nos,
        pier_xs=pier_xs,
    )


def build_span_map(lm: Landmarks, old: list[float], new: list[float]) -> SpanMap:
    if len(old) != 3 or len(new) != 3:
        raise RuntimeError("spanremap 只支持悬浇三跨,请用 30+50+30 这种三个数字")
    d1, d2, d3 = new[0] - old[0], new[1] - old[1], new[2] - old[2]
    left_cip = (lm.B - lm.A) + d1
    right_cip = (lm.H - lm.G) + d3
    gap_l = (lm.midL - lm.TLi) + d2 / 2.0
    gap_r = (lm.TRi - lm.midR) + d2 / 2.0
    if left_cip < MIN_ZONE:
        raise RuntimeError(
            f"左边跨现浇段会被拉到 {left_cip:.3f}m(<{MIN_ZONE}m),换更大边跨的近邻"
        )
    if right_cip < MIN_ZONE:
        raise RuntimeError(
            f"右边跨现浇段会被拉到 {right_cip:.3f}m(<{MIN_ZONE}m),换更大边跨的近邻"
        )
    if gap_l < MIN_ZONE or gap_r < MIN_ZONE:
        raise RuntimeError(
            f"中跨恒高段会被拉到 {min(gap_l, gap_r):.3f}m(<{MIN_ZONE}m),换更大中跨的近邻"
        )

    old_ks = [lm.A, lm.B, lm.C, lm.TLi, lm.midL, lm.midR, lm.TRi, lm.F, lm.G, lm.H]
    new_ks = [
        lm.A,
        lm.B + d1,
        lm.C + d1,
        lm.TLi + d1,
        lm.TLi + d1 + (lm.midL - lm.TLi) + d2 / 2.0,
        lm.TLi + d1 + (lm.midL - lm.TLi) + d2 / 2.0 + (lm.midR - lm.midL),
        lm.TRi + d1 + d2,
        lm.F + d1 + d2,
        lm.G + d1 + d2,
        lm.H + d1 + d2 + d3,
    ]
    # 合并几乎重合的控制点,避免除零
    o2: list[float] = []
    n2: list[float] = []
    for a, b in zip(old_ks, new_ks):
        if o2 and abs(a - o2[-1]) < 1e-6:
            n2[-1] = b
            continue
        o2.append(a)
        n2.append(b)
    return SpanMap(
        old_ks=o2,
        new_ks=n2,
        A=lm.A,
        H=lm.H,
        A_new=lm.A,
        H_new=n2[-1],
        old_spans=old,
        new_spans=new,
        dL=(d1, d2, d3),
    )


def remap_nodes_text(text: str, nodes: dict[int, Node], sm: SpanMap) -> str:
    lines = text.splitlines(keepends=True)
    for nd in nodes.values():
        new_x = sm.global_x(nd.x)
        line = lines[nd.line_i]
        m = NODE_RE.search(line)
        if not m:
            continue
        lines[nd.line_i] = (
            line[: m.start(4)] + fmt_num(new_x, nd.raw_x) + line[m.end(4) :]
        )
    return "".join(lines)


def _strip_curve_base(name: str) -> str:
    for suf in ("_HorCurve", "_VerCurve", "_Curve"):
        if name.endswith(suf):
            return name[: -len(suf)]
    return name


def _group_xmin(
    name: str,
    groups: dict[str, list[int]],
    beams: dict[int, tuple[int, int]],
    nodes: dict[int, Node],
) -> float | None:
    base = _strip_curve_base(name)
    for gname in (base + "Gp", base + "_CurveGp", name + "Gp"):
        eids = groups.get(gname) or []
        xs = _elem_xs(beams, nodes, eids)
        if xs:
            return min(xs)
    return None


def _is_local_arc2d(xs: list[float], gmin: float | None) -> bool:
    if not xs:
        return False
    return min(xs) < 2.0 and gmin is not None and gmin > 5.0


def remap_geometry_text(
    text: str,
    sm: SpanMap,
    groups: dict[str, list[int]],
    beams: dict[int, tuple[int, int]],
    nodes: dict[int, Node],
) -> tuple[str, int]:
    count = 0

    def map_x(x: float, local: bool, gmin: float) -> float:
        if not local:
            return sm.global_x(x)
        return sm.global_x(gmin + x) - sm.global_x(gmin)

    def repl(m: re.Match[str]) -> str:
        nonlocal count
        name, kind, args = m.group(2), m.group(3), m.group(4)
        stride = 3 if kind == "ARC2D" else 4
        nums = list(NUM_RE.finditer(args))
        xs = [float(nums[i].group()) for i in range(0, len(nums), stride)]
        gmin = _group_xmin(name, groups, beams, nodes)
        local = kind == "ARC2D" and _is_local_arc2d(xs, gmin)
        gmin_v = gmin if gmin is not None else 0.0
        out = args
        for i in reversed(range(0, len(nums), stride)):
            tok = nums[i]
            mapped = map_x(float(tok.group()), local, gmin_v)
            out = out[: tok.start()] + fmt_num(mapped, tok.group()) + out[tok.end() :]
        count += 1
        return m.group(1) + out + m.group(5)

    new_text = GEOM_RE.sub(repl, text)
    return new_text, count


def update_portrait(path: Path, new_spans: list[float], dry_run: bool) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    total = sum(new_spans)
    total_s = str(int(total)) if abs(total - round(total)) < 1e-9 else f"{total:g}"
    pretty = " + ".join(
        str(int(x)) if x == int(x) else str(x) for x in new_spans
    )

    def repl(m: re.Match[str]) -> str:
        return f"跨径:{pretty}m,总长 {total_s}m"

    new_text, n = SPAN_LINE_RE.subn(repl, text, count=1)
    if n == 0:
        return False
    if not dry_run and new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return True


def checks(nodes: dict[int, Node], lm: Landmarks, sm: SpanMap) -> list[str]:
    deck = [sm.global_x(nodes[n].x) for n in lm.deck_nos]
    msgs: list[str] = []
    if any(b - a < -1e-6 for a, b in zip(deck, deck[1:])):
        msgs.append("主梁节点 x 非单调递增")
    else:
        msgs.append("单调 OK")
    span_sum = sum(sm.new_spans)
    beam_len = deck[-1] - deck[0]
    old_over = (lm.H - lm.A) - sum(sm.old_spans)
    expect = span_sum + old_over
    if abs(beam_len - (lm.H - lm.A + sum(sm.dL))) > 1e-3:
        msgs.append(f"梁端间距 {beam_len:.4f} 与 ΔL 不一致")
    else:
        msgs.append(f"总长 {beam_len:.2f} (跨径和 {span_sum:g})")
    # 半中跨:墩1 → 跨中
    if len(lm.pier_xs) >= 2:
        p1, p2 = sm.global_x(lm.pier_xs[0]), sm.global_x(lm.pier_xs[1])
        mid = 0.5 * (sm.global_x(lm.midL) + sm.global_x(lm.midR))
        half = abs(mid - p1)
        if abs(half - sm.new_spans[1] / 2.0) > 0.05:
            msgs.append(f"半中跨闭合失败: {half:.3f} vs {sm.new_spans[1]/2:.3f}")
        else:
            msgs.append("半中跨闭合 OK")
        if abs(p2 - p1 - sm.new_spans[1]) > 0.05:
            msgs.append(f"墩距 {p2-p1:.3f} ≠ 中跨 {sm.new_spans[1]:g}")
    if abs(sm.new_spans[0] - sm.new_spans[2]) < 1e-6:
        center = 0.5 * (deck[0] + deck[-1])
        n = len(deck)
        worst = 0.0
        for i in range(n):
            worst = max(worst, abs((deck[i] + deck[n - 1 - i]) / 2.0 - center))
        if worst > 0.05:
            msgs.append(f"左右镜像偏差 {worst:.3f}m")
        else:
            msgs.append("左右镜像 OK")
    cl = sm.global_x(lm.midR) - sm.global_x(lm.midL)
    msgs.append(f"中跨合龙 {cl:.2f}m")
    return msgs


def default_dest() -> Path:
    try:
        from pyosis import OSISEngine

        raw = OSISEngine().project.get_directory() or ""
    except Exception as e:
        raise RuntimeError(f"无法读取当前 OSIS 工程目录: {e}") from e
    if not str(raw).strip():
        raise RuntimeError("当前没有打开的 OSIS 工程(get_directory 为空)")
    return Path(raw)


def resolve_prep(ns: argparse.Namespace) -> Path:
    if ns.prep:
        p = Path(ns.prep).resolve()
        if p.name != "prep" and (p / "prep").is_dir():
            p = p / "prep"
        return p
    dest = Path(ns.dest).resolve() if ns.dest else default_dest()
    return (dest / "py" / "prep").resolve()


def find_portrait(prep: Path) -> Path | None:
    for cand in (prep.parent / "项目画像.md", prep / "项目画像.md"):
        if cand.is_file():
            return cand
    return None


def infer_old_spans(ns: argparse.Namespace, prep: Path) -> list[float]:
    if ns.src:
        spans = parse_spans(ns.src.replace(" ", ""))
        if not spans:
            spans = parse_spans(ns.src)
        if spans:
            return spans
    portrait = find_portrait(prep)
    if portrait:
        spans = parse_spans(portrait.read_text(encoding="utf-8"))
        if spans:
            return spans
    for part in (prep.parent.name, prep.parent.parent.name):
        spans = parse_spans(part)
        if spans:
            return spans
    raise RuntimeError("无法确定原跨径,请加 --from 30+50+30 或保证 py/项目画像.md 有跨径行")


def run(ns: argparse.Namespace) -> int:
    new_spans = parse_spans(ns.to.replace(" ", "") if ns.to else "")
    if not new_spans:
        new_spans = parse_spans(ns.to or "")
    if len(new_spans) != 3:
        print("错误: --to 必须是三跨,例如 35+50+35", file=sys.stderr)
        return 1
    prep = resolve_prep(ns)
    node_p = prep / "_5_node.py"
    elem_p = prep / "_6_element.py"
    prop_p = prep / "_2_property.py"
    for p in (node_p, elem_p, prop_p):
        if not p.is_file():
            print(f"错误: 缺少 {p}", file=sys.stderr)
            return 1
    old_spans = infer_old_spans(ns, prep)
    if len(old_spans) != 3:
        print("错误: 原跨径不是三跨,spanremap 只支持悬浇三跨", file=sys.stderr)
        return 1
    if all(abs(a - b) < 1e-9 for a, b in zip(old_spans, new_spans)):
        print(f"spanremap: 已是 {format_spans(new_spans)},无需改")
        return 0

    node_text = node_p.read_text(encoding="utf-8")
    elem_text = elem_p.read_text(encoding="utf-8")
    prop_text = prop_p.read_text(encoding="utf-8")
    nodes = parse_nodes(node_text)
    beams, groups = parse_beams_and_groups(elem_text)
    lm = build_landmarks(nodes, beams, groups)
    sm = build_span_map(lm, old_spans, new_spans)
    new_node = remap_nodes_text(node_text, nodes, sm)
    new_prop, ncurve = remap_geometry_text(prop_text, sm, groups, beams, nodes)
    msgs = checks(nodes, lm, sm)
    bad = [m for m in msgs if any(k in m for k in ("非单调", "失败", "不一致", "偏差", "≠"))]
    if bad:
        print("错误: 改跨校核未过:", file=sys.stderr)
        for m in msgs:
            print(f"  {m}", file=sys.stderr)
        return 1

    pier_new = [sm.global_x(x) for x in lm.pier_xs]
    lines = [
        "spanremap",
        f"prep: {prep}",
        f"跨径: {format_spans(old_spans)} → {format_spans(new_spans)}",
        f"节点: {len(nodes)}  梁端 {sm.A_new:.2f} → {sm.H_new:.2f}  "
        f"墩 {', '.join(f'{x:.1f}' for x in pier_new) or '-'}",
        f"合龙: 边 {lm.C - lm.B:.2f}m / 中 {lm.midR - lm.midL:.2f}m (保持)",
        f"钢束曲线: {ncurve} 条,已改 x",
        "校核: " + "  ".join(msgs),
        "未改: _6 _7 _8 _9 _10",
    ]
    if ns.dry_run:
        lines.append("动作: dry-run,未写文件")
        print("\n".join(lines))
        return 0
    node_p.write_text(new_node, encoding="utf-8")
    prop_p.write_text(new_prop, encoding="utf-8")
    portrait = find_portrait(prep)
    if portrait:
        update_portrait(portrait, new_spans, dry_run=False)
        lines.append(f"画像: {portrait.name} 已更新跨径")
    print("\n".join(lines))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="spanremap",
        description="悬浇三跨改跨径:只改 _5 x 和 _2 钢束曲线 x",
        add_help=True,
    )
    p.add_argument("--to", dest="to", default="", help="目标跨径,如 35+50+35")
    p.add_argument("--from", dest="src", default="", help="原跨径,默认读项目画像")
    p.add_argument("--prep", default="", help="prep 目录,默认 dest/py/prep")
    p.add_argument("--dest", default="", help="工程根目录,默认 get_directory()")
    p.add_argument("--dry-run", action="store_true", help="只校核不写文件")
    return p


def main() -> int:
    _configure_stdio()
    args = sys.argv[1:]
    if not args:
        print(USAGE, file=sys.stderr)
        return 1
    parser = build_parser()
    try:
        ns = parser.parse_args(args)
    except SystemExit as e:
        code = e.code
        return 0 if code in (0, None) else 1
    ns.to = (ns.to or "").strip()
    ns.src = (ns.src or "").strip()
    ns.prep = (ns.prep or "").strip()
    ns.dest = ns.dest.strip() or None
    try:
        return run(ns)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
