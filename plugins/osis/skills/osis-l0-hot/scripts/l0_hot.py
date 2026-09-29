#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0 热操作 CLI：写回 OSIS + 可选同步 prep/.py；校验在函数内完成，调用方不必手写 assert。

用法示例:
  python l0_hot.py list
  python l0_hot.py nforce --case 端横梁荷载工况 --node 2 --fz -21000 --prep path/to/_8_loadcase.py
  python l0_hot.py stage --no 4 --name CS4_体系转换 --duration 15 --prep path/to/_10_stage.py
  python l0_hot.py gravity --case 预制单元自重 --z -1.05 --prep path/to/_8_loadcase.py
  python l0_hot.py gravity --all --z -1.02 --prep path/to/_8_loadcase.py
  python l0_hot.py settlement --name 沉降组1 --setl -0.06 --nodes 2 --prep path/to/_9_analysis.py
  python l0_hot.py humidity --no 1 --name 收缩徐变 --humidity 70 --birth 7 --type-coeff 5 --shrink-birth 3 --prep path/to/_3_material.py
  python l0_hot.py pst --case 预应力顶板束 --shape T1-1 --stress 1400000000 --prep path/to/_8_loadcase.py
  python l0_hot.py lane --name 车道 --length 16.0 --prep path/to/_9_analysis.py
  python l0_hot.py line --case 铺装工况 --fz -7500 --prep path/to/_8_loadcase.py
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from pathlib import Path


def _engine():
    from pyosis import OSISEngine

    return OSISEngine()


def _ok(msg: str) -> None:
    print(f"OK: {msg}")


def _fail(msg: str, code: int = 1) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _patch_file(
    path: Path,
    pattern: str,
    repl: str | Callable[[re.Match[str]], str],
    flags: int = 0,
) -> None:
    text = path.read_text(encoding="utf-8")
    new, n = re.subn(pattern, repl, text, count=1, flags=flags)
    if n != 1:
        _fail(f"未能在 {path} 精确替换 1 处(实际 {n}): pattern={pattern!r}")
    path.write_text(new, encoding="utf-8")
    print(f"EDIT: {path}")


def _fmt_num(v: float) -> str:
    """与 prep 模板常见写法对齐: -7500.0"""
    if abs(float(v) - round(float(v))) < 1e-9:
        return f"{int(round(float(v)))}.0"
    return repr(float(v))


def _patch_line_fz(path: Path, case: str, fz: float) -> None:
    """把 for-i 循环里 create('LINE', i, ...) 的 I/J 端 Fz 同步为新值。"""
    text = path.read_text(encoding="utf-8")
    pat = re.compile(
        rf'(engine\.load\.get\(\s*[\'"]'
        + re.escape(case)
        + rf'[\'"]\s*\)\.create\(\s*[\'"]LINE[\'"]\s*,\s*i\s*,\s*)([^)]+)(\))'
    )
    m = pat.search(text)
    if not m:
        _fail(f"未能在 {path} 找到 create('LINE', i, ...) for case={case!r}")
    parts = [p.strip() for p in m.group(2).split(",")]
    # create("LINE", i, ...) 之后: coord,type, offsetI(3), FI(6), offsetJ(3), FJ(6) = 20
    if len(parts) != 20:
        _fail(f"LINE 参数个数期望 20,实际 {len(parts)}: {parts!r}")
    # FZI=index 7 (0-based in parts), FZJ=index 16
    parts[7] = _fmt_num(fz)
    parts[16] = _fmt_num(fz)
    new_call = m.group(1) + ", ".join(parts) + m.group(3)
    new_text = text[: m.start()] + new_call + text[m.end() :]
    if new_text == text:
        # 已是目标值也算成功(幂等)
        print(f"EDIT: {path} (unchanged)")
        return
    path.write_text(new_text, encoding="utf-8")
    print(f"EDIT: {path}")


# ── ops ──────────────────────────────────────────────


def op_stage(args: argparse.Namespace) -> None:
    e = _engine()
    e.stage.create(args.no, args.name, args.duration)
    got = e.stage.get(args.no).duration
    if abs(float(got) - float(args.duration)) > 1e-9:
        _fail(f"stage {args.no} duration 读回 {got} != {args.duration}")
    if args.prep:
        # stage.create(no, "name", old) → new duration
        pat = (
            rf'(engine\.stage\.create\(\s*{args.no}\s*,\s*[\'"]'
            + re.escape(args.name)
            + rf'[\'"]\s*,\s*)(-?\d+(?:\.\d+)?)(\s*\))'
        )
        _patch_file(Path(args.prep), pat, rf"\g<1>{args.duration}\3")
    _ok(f"stage {args.no} {args.name!r} duration={args.duration}")


def op_settlement(args: argparse.Namespace) -> None:
    e = _engine()
    nodes = [int(x) for x in args.nodes]
    e.settlement.group.create(args.name, args.setl, *nodes)
    g = e.settlement.group.get(args.name)
    if abs(float(g.setl) - float(args.setl)) > 1e-9:
        _fail(f"settlement {args.name!r} setl 读回 {g.setl} != {args.setl}")
    if args.prep:
        node_part = r"\s*,\s*".join(str(n) for n in nodes)
        pat = (
            rf'(engine\.settlement\.group\.create\(\s*[\'"]'
            + re.escape(args.name)
            + rf'[\'"]\s*,\s*)(-?\d+(?:\.\d+)?)(\s*,\s*{node_part}\s*\))'
        )
        _patch_file(Path(args.prep), pat, rf"\g<1>{args.setl}\3")
    _ok(f"settlement {args.name!r} setl={args.setl} nodes={nodes}")


def _gravity_cases_from_prep(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    names = re.findall(
        r'engine\.load\.get\(\s*[\'"]([^\'"]+)[\'"]\s*\)\.create\(\s*[\'"]GRAVITY[\'"]',
        text,
    )
    # 保序去重
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def op_gravity(args: argparse.Namespace) -> None:
    """改 GRAVITY z。支持单/多工况,或 --all 覆盖全部含自重的工况。"""
    e = _engine()
    z = float(args.z)
    if args.all_cases:
        if args.prep:
            cases = _gravity_cases_from_prep(Path(args.prep))
        else:
            cases = [
                lc.name
                for lc in e.load.all()
                if getattr(lc, "gravity", None) is not None
            ]
        if not cases:
            _fail("gravity --all: 未找到含 GRAVITY 的工况(检查 --prep 或现网)")
    elif args.case:
        cases = list(args.case)
    else:
        _fail("gravity 需要 --case NAME [NAME ...] 或 --all")

    bad_missing = []
    for name in cases:
        lc = e.load.get(name)
        if lc is None:
            bad_missing.append(name)
            continue
        lc.create("GRAVITY", 0.0, 0.0, z)
    if bad_missing:
        _fail(f"gravity 工况不存在: {bad_missing}")

    bad_read = []
    for name in cases:
        got = e.load.get(name).gravity
        if got is None or abs(float(got["xyz"][2]) - z) > 1e-9:
            bad_read.append((name, None if got is None else got["xyz"][2]))
    if bad_read:
        _fail(f"gravity z 读回失败: {bad_read[:5]}")

    if args.prep:
        path = Path(args.prep)
        text = path.read_text(encoding="utf-8")
        new = text
        for name in cases:
            pat = (
                rf'(engine\.load\.get\(\s*[\'"]'
                + re.escape(name)
                + rf'[\'"]\s*\)\.create\(\s*[\'"]GRAVITY[\'"]\s*,\s*0\.0\s*,\s*0\.0\s*,\s*)'
                + rf'(-?\d+(?:\.\d+)?)(\s*\))'
            )
            new2, n = re.subn(pat, rf"\g<1>{_fmt_num(z)}\3", new, count=1)
            if n != 1:
                _fail(f"未能在 {path} 精确替换工况 {name!r} 的 GRAVITY 1 处(实际 {n})")
            new = new2
        if new != text:
            path.write_text(new, encoding="utf-8")
            print(f"EDIT: {path} ({len(cases)} cases)")
        else:
            print(f"EDIT: {path} (unchanged, {len(cases)} cases)")
    if len(cases) == 1:
        _ok(f"gravity {cases[0]!r} z={z}")
    else:
        _ok(f"gravity z={z} cases={len(cases)}")


def op_nforce(args: argparse.Namespace) -> None:
    e = _engine()
    fx, fy, fz = args.fx, args.fy, args.fz
    mx, my, mz = args.mx, args.my, args.mz
    e.load.get(args.case).create("NFORCE", args.node, fx, fy, fz, mx, my, mz)
    hits = [
        x
        for x in e.load.get(args.case).nforce
        if int(x.get("entityNO", -1)) == int(args.node)
        or int(x.get("no", -1)) == int(args.node)
    ]
    if not hits:
        _fail(f"nforce 读回无节点 {args.node}: {e.load.get(args.case).nforce}")
    p = hits[0]["p"]
    if abs(float(p[2]) - float(fz)) > 1e-6:
        _fail(f"nforce 节点 {args.node} p[2] 读回 {p[2]} != {fz}")
    if args.prep:
        # 只替换该节点那一行的 Fz（第 5 个数值参数，索引从 create 后）
        pat = (
            rf'(engine\.load\.get\(\s*[\'"]'
            + re.escape(args.case)
            + rf'[\'"]\s*\)\.create\(\s*[\'"]NFORCE[\'"]\s*,\s*{args.node}\s*,\s*)'
            rf'(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)'
            rf'(\s*,\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*\))'
        )
        _patch_file(
            Path(args.prep),
            pat,
            rf"\g<1>{fx}, {fy}, {fz}\5",
        )
    _ok(f"nforce {args.case!r} node={args.node} Fz={fz} (p={p})")


def op_humidity(args: argparse.Namespace) -> None:
    e = _engine()
    e.prop.creep_shrink.create(
        args.no,
        args.name,
        args.humidity,
        args.birth,
        args.type_coeff,
        args.shrink_birth,
    )
    cs = e.prop.creep_shrink.get(args.no)
    got = float(cs.avg_humidity)
    if abs(got - float(args.humidity)) > 1e-9:
        _fail(f"humidity 读回 {got} != {args.humidity}")
    if args.prep:
        pat = (
            rf'(engine\.prop\.creep_shrink\.create\(\s*{args.no}\s*,\s*[\'"]'
            + re.escape(args.name)
            + rf'[\'"]\s*,\s*)(-?\d+(?:\.\d+)?)'
        )
        _patch_file(Path(args.prep), pat, rf"\g<1>{args.humidity}")
    _ok(f"creep_shrink no={args.no} humidity={args.humidity}")


def _pst_prep_pattern(case: str, shape: str, method: str, force_name: str) -> str:
    return (
        rf'(engine\.load\.get\(\s*[\'"]'
        + re.escape(case)
        + rf'[\'"]\s*\)\.create\(\s*[\'"]PST[\'"]\s*,\s*[\'"]'
        + re.escape(shape)
        + rf'[\'"]\s*,\s*[\'"]'
        + re.escape(method)
        + rf'[\'"]\s*,\s*[\'"]'
        + re.escape(force_name)
        + rf'[\'"]\s*,\s*)(-?\d+(?:\.\d+)?)(\s*,\s*)(-?\d+(?:\.\d+)?)'
    )


def _patch_pst_prep(
    path: Path, case: str, shape: str, method: str, force_name: str, stress: float
) -> None:
    s = _fmt_num(stress)
    # 禁止 rf"\g<1>{s}\3{s}"：stress=1395000000.0 时 \3 与后续 1 粘成 \313（U+00CB），
    # cr-003 的 _8 PST 行会变成 1395000000.0Ë95000000.0，main.py SyntaxError。
    _patch_file(
        path,
        _pst_prep_pattern(case, shape, method, force_name),
        lambda m: f"{m.group(1)}{s}{m.group(3)}{s}",
    )


def op_pst(args: argparse.Namespace) -> None:
    e = _engine()
    stress = args.stress
    e.load.get(args.case).create(
        "PST", args.shape, args.method, args.force_name, stress, stress
    )
    items = e.load.get(args.case).prestressed or []
    hits = [x for x in items if x.get("name") == args.shape or x.get("keyName") == args.shape]
    if not hits:
        _fail(f"pst 读回无 shape {args.shape!r}: {items}")
    if abs(float(hits[0]["beg"]) - float(stress)) > 1.0:
        _fail(f"pst {args.shape} beg 读回 {hits[0]['beg']} != {stress}")
    if args.prep:
        _patch_pst_prep(
            Path(args.prep),
            args.case,
            args.shape,
            args.method,
            args.force_name,
            stress,
        )
    _ok(f"pst {args.case!r} shape={args.shape} stress={stress}")


def _line_elem_no(item: dict) -> int:
    return int(item.get("entityNO", item.get("no", -1)))


def op_line(args: argparse.Namespace) -> None:
    """改工况下 LINE 线荷载竖向力 Fz(I/J 同值)。delete+重建,避免残留。"""
    e = _engine()
    lc = e.load.get(args.case)
    if lc is None:
        _fail(f"load case {args.case!r} 不存在")

    existing = list(lc.line or [])
    by_no = {_line_elem_no(x): x for x in existing if _line_elem_no(x) >= 0}

    if args.elems:
        targets = [int(x) for x in args.elems]
    elif args.elem_from is not None:
        if args.elem_to is None:
            _fail("指定 --elem-from 时必须同时给 --elem-to")
        targets = list(range(int(args.elem_from), int(args.elem_to) + 1))
    else:
        targets = sorted(by_no.keys())
    if not targets:
        _fail(f"line {args.case!r}: 无目标单元(现网无 LINE 且未给 --elems/--elem-from)")

    fz = float(args.fz)
    for no in targets:
        item = by_no.get(no)
        if item is not None:
            coord = 1 if item.get("globalCoor") else 0
            load_type = 1 if item.get("discreteLineLoad") else 0
            oi = list(item.get("offsetI") or [0.0, 0.0, 0.0])
            oj = list(item.get("offsetJ") or [1.0, 0.0, 0.0])
            pi = list(item.get("pI") or [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            pj = list(item.get("pJ") or [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            while len(oi) < 3:
                oi.append(0.0)
            while len(oj) < 3:
                oj.append(0.0)
            while len(pi) < 6:
                pi.append(0.0)
            while len(pj) < 6:
                pj.append(0.0)
            pi[2] = fz
            pj[2] = fz
            lc.delete("LINE", no)
            lc.create(
                "LINE",
                no,
                coord,
                load_type,
                float(oi[0]),
                float(oi[1]),
                float(oi[2]),
                float(pi[0]),
                float(pi[1]),
                float(pi[2]),
                float(pi[3]),
                float(pi[4]),
                float(pi[5]),
                float(oj[0]),
                float(oj[1]),
                float(oj[2]),
                float(pj[0]),
                float(pj[1]),
                float(pj[2]),
                float(pj[3]),
                float(pj[4]),
                float(pj[5]),
            )
        else:
            # 模板默认: 单元坐标+连续, I@0 / J@1, 仅 Fz
            lc.create(
                "LINE",
                no,
                0,
                0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                fz,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                fz,
                0.0,
                0.0,
                0.0,
            )

    # 重新取对象,避免沿用旧 list 引用
    lc = e.load.get(args.case)
    got = { _line_elem_no(x): x for x in (lc.line or []) }
    bad = []
    for no in targets:
        item = got.get(no)
        if item is None:
            bad.append(f"{no}:missing")
            continue
        pi = item.get("pI") or []
        pj = item.get("pJ") or []
        if len(pi) < 3 or abs(float(pi[2]) - fz) > 1e-6:
            bad.append(f"{no}:pI={pi}")
        if len(pj) < 3 or abs(float(pj[2]) - fz) > 1e-6:
            bad.append(f"{no}:pJ={pj}")
    if bad:
        _fail(f"line {args.case!r} Fz 读回失败: {bad[:5]}")

    if args.prep:
        _patch_line_fz(Path(args.prep), args.case, fz)
    _ok(f"line {args.case!r} Fz={fz} elems={len(targets)} ({targets[0]}..{targets[-1]})")


def op_lane(args: argparse.Namespace) -> None:
    """改车道长度(同名 create 覆盖)。未显式传入的其它参数优先沿用现网车道。"""
    e = _engine()
    existing = e.live.lane.get(args.name)
    lane_type = args.lane_type
    wheel = args.wheel
    veh_ori = args.veh_ori
    ref_flag = args.ref_flag
    ref_group = args.ref_group
    oy, oz = args.oy, args.oz

    if existing is not None:
        if wheel is None:
            wheel = float(existing.wheel_width)
        if veh_ori is None:
            veh_ori = int(existing.veh_ori)
        if ref_group is None:
            ref_group = existing.ref_long_ele_grp or "主梁单元"
        if oy is None:
            oy = float((existing.offset or [0, 0, 0])[1] if len(existing.offset or []) > 1 else 0.0)
        if oz is None:
            oz = float((existing.offset or [0, 0, 0])[2] if len(existing.offset or []) > 2 else 0.0)
        # lane_def_method False → 模板里常见的 0
        if ref_flag is None:
            ref_flag = 0 if not existing.lane_def_method else 1
    else:
        if wheel is None:
            wheel = 1.8
        if veh_ori is None:
            veh_ori = 1
        if ref_flag is None:
            ref_flag = 0
        if ref_group is None:
            ref_group = "主梁单元"
        if oy is None:
            oy = 0.0
        if oz is None:
            oz = 0.0

    e.live.lane.create(
        args.name,
        lane_type,
        args.length,
        wheel,
        veh_ori,
        ref_flag,
        ref_group,
        oy,
        oz,
    )
    got = e.live.lane.get(args.name)
    if got is None or abs(float(got.length) - float(args.length)) > 1e-9:
        _fail(f"lane {args.name!r} length 读回 {getattr(got, 'length', None)} != {args.length}")
    if args.prep:
        # live.lane.create("车道", "VE", 15.0, ...) → 只换长度(第 3 个数值参数)
        pat = (
            rf'(engine\.live\.lane\.create\(\s*[\'"]'
            + re.escape(args.name)
            + rf'[\'"]\s*,\s*[\'"]'
            + re.escape(lane_type)
            + rf'[\'"]\s*,\s*)(-?\d+(?:\.\d+)?)'
        )
        _patch_file(Path(args.prep), pat, rf"\g<1>{args.length}")
    _ok(
        f"lane {args.name!r} length={args.length} "
        f"(type={lane_type}, wheel={wheel}, ori={veh_ori}, ref={ref_group})"
    )


def op_list(_: argparse.Namespace) -> None:
    rows = [
        ("stage", "改施工阶段 duration", "stage --no N --name NAME --duration D [--prep _10]"),
        ("settlement", "改沉降组 setl", "settlement --name N --setl V --nodes 2 [3..] [--prep _9]"),
        ("gravity", "改自重 z(可批量/--all)", "gravity --z Z (--case N [N..] | --all) [--prep _8]"),
        ("nforce", "改单节点竖向力 Fz", "nforce --case NAME --node N --fz FZ [--prep _8]"),
        ("humidity", "改收缩徐变年平均湿度", "humidity --no 1 --name 收缩徐变 --humidity H ... [--prep _3]"),
        ("pst", "改单束张拉应力", "pst --case NAME --shape S --stress P [--prep _8]"),
        ("lane", "改车道长度", "lane --name 车道 --length L [--prep _9]"),
        ("line", "改 LINE 线荷载 Fz", "line --case 铺装工况 --fz FZ [--elem-from 1 --elem-to 18] [--prep _8]"),
    ]
    print("available ops:")
    for name, desc, usage in rows:
        print(f"  {name:12} {desc}")
        print(f"               {usage}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="OSIS L0 热操作（写回+内置校验+可选改 prep）")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("list", help="列出可用操作")
    s.set_defaults(func=op_list)

    s = sub.add_parser("stage", help="改 stage duration")
    s.add_argument("--no", type=int, required=True)
    s.add_argument("--name", required=True)
    s.add_argument("--duration", type=float, required=True)
    s.add_argument("--prep", default="")
    s.set_defaults(func=op_stage)

    s = sub.add_parser("settlement", help="改沉降组 setl")
    s.add_argument("--name", required=True)
    s.add_argument("--setl", type=float, required=True)
    s.add_argument("--nodes", nargs="+", required=True)
    s.add_argument("--prep", default="")
    s.set_defaults(func=op_settlement)

    s = sub.add_parser("gravity", help="改 GRAVITY z(支持多工况或 --all)")
    s.add_argument("--case", nargs="+", default=None, help="一个或多个工况名")
    s.add_argument("--all", action="store_true", dest="all_cases", help="现网全部含 GRAVITY 的工况")
    s.add_argument("--z", type=float, required=True)
    s.add_argument("--prep", default="")
    s.set_defaults(func=op_gravity)

    s = sub.add_parser("nforce", help="改 NFORCE Fz（默认同节点其它分量为 0）")
    s.add_argument("--case", required=True)
    s.add_argument("--node", type=int, required=True)
    s.add_argument("--fz", type=float, required=True)
    s.add_argument("--fx", type=float, default=0.0)
    s.add_argument("--fy", type=float, default=0.0)
    s.add_argument("--mx", type=float, default=0.0)
    s.add_argument("--my", type=float, default=0.0)
    s.add_argument("--mz", type=float, default=0.0)
    s.add_argument("--prep", default="")
    s.set_defaults(func=op_nforce)

    s = sub.add_parser("humidity", help="改 creep_shrink 年平均湿度")
    s.add_argument("--no", type=int, required=True)
    s.add_argument("--name", default="收缩徐变")
    s.add_argument("--humidity", type=float, required=True)
    s.add_argument("--birth", type=int, default=7)
    s.add_argument("--type-coeff", type=float, default=5.0, dest="type_coeff")
    s.add_argument("--shrink-birth", type=int, default=3, dest="shrink_birth")
    s.add_argument("--prep", default="")
    s.set_defaults(func=op_humidity)

    s = sub.add_parser("pst", help="改 PST 张拉应力(两端同值)")
    s.add_argument("--case", required=True)
    s.add_argument("--shape", required=True)
    s.add_argument("--stress", type=float, required=True)
    s.add_argument("--method", default="BOTH")
    s.add_argument("--force-name", default="ST", dest="force_name")
    s.add_argument("--prep", default="")
    s.set_defaults(func=op_pst)

    s = sub.add_parser("lane", help="改车道长度(同名覆盖;其它参数默认同现网)")
    s.add_argument("--name", required=True)
    s.add_argument("--length", type=float, required=True)
    s.add_argument("--lane-type", default="VE", dest="lane_type")
    s.add_argument("--wheel", type=float, default=None)
    s.add_argument("--veh-ori", type=int, default=None, dest="veh_ori")
    s.add_argument("--ref-flag", type=int, default=None, dest="ref_flag")
    s.add_argument("--ref-group", default=None, dest="ref_group")
    s.add_argument("--oy", type=float, default=None)
    s.add_argument("--oz", type=float, default=None)
    s.add_argument("--prep", default="")
    s.set_defaults(func=op_lane)

    s = sub.add_parser("line", help="改 LINE 线荷载 Fz(I/J 同值;delete+重建)")
    s.add_argument("--case", required=True)
    s.add_argument("--fz", type=float, required=True)
    s.add_argument("--elems", nargs="+", default=None, help="显式单元号列表")
    s.add_argument("--elem-from", type=int, default=None, dest="elem_from")
    s.add_argument("--elem-to", type=int, default=None, dest="elem_to")
    s.add_argument("--prep", default="")
    s.set_defaults(func=op_line)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
