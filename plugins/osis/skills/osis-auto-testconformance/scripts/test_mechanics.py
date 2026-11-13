"""受力评分:在临时工程里求解,用几个结果判断模型受力上有没有大错。与构造评分(test_conformance.py)并列。

不动用户的模型:把模型导出到临时工程 <scratch>/model,在仅求解器模式下重建、改施工阶段、求解、读结果。
分三步跑(前两步连的 OSIS 实例不同,所以合不成一步):

    # 第 1 步 准备,连当前实例(读代码模式用普通 python 也行):导出模型,写第 2 步的启动脚本,打印其路径
    python test_mechanics.py [--tier fast|stage|full] [--candidate-dir <py 目录>]
    # 第 2 步 求解,instance_id="solver":跑第 1 步打印的 <scratch>/model/py/_mechanics.py,stdout 是报告
    # 第 3 步 清理(求解输出可达几个 GB):
    python test_mechanics.py --cleanup [--scratch PATH | --candidate-dir <py 目录>]

三档(评的维度见 DIMS):
    fast   快速档:所有施工阶段压成一个阶段。评 D1~D5(应力在有体系转换的桥上不可信,不评)
    stage  施工阶段档:保留施工阶段,算到成桥为止(去掉徐变十年和运营阶段)。加评 D6 成桥应力、D7 施工阶段应力
    full   完整档:全部阶段原样求解。加评 D8 长期应力(徐变十年后)

退出码同 test_conformance.py:0 = 总分 ≥ 0.5;1 = 总分 < 0.5;2 = 没评成。
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# JTG 3362-2018 表 3.1.3:混凝土等级 → (fck, ftk),MPa
STRENGTH = {20: (13.4, 1.54), 25: (16.7, 1.78), 30: (20.1, 2.01), 35: (23.4, 2.20), 40: (26.8, 2.40),
            45: (29.6, 2.51), 50: (32.4, 2.65), 55: (35.5, 2.74), 60: (38.5, 2.85), 65: (41.5, 2.93),
            70: (44.5, 3.00), 75: (47.4, 3.05), 80: (50.2, 3.10)}
TIERS = {"fast": "快速档(所有施工阶段压成一个阶段)", "stage": "施工阶段档(算到成桥,不算徐变十年和运营阶段)",
         "full": "完整档(全部阶段)"}
DIMS = {"D1": "混凝土等级", "D2": "预应力平衡度", "D3": "支座反力", "D4": "荷载总量", "D5": "恒载挠度",
        "D6": "成桥应力", "D7": "施工阶段应力", "D8": "长期应力"}
LAUNCHER = "_mechanics.py"


def lerp(x: float, x0: float, x1: float, y0: float = 1.0, y1: float = 0.0) -> float:
    """x ≤ x0 → y0,x ≥ x1 → y1,中间线性。"""
    if x <= x0:
        return y0
    if x >= x1:
        return y1
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def status(score: float) -> str:
    return "符合要求" if score >= 0.9 else "基本符合" if score >= 0.5 else "不符合"


def rating(score: float) -> str:  # 同构造评分的评级
    return ("优秀" if score >= 1.0 - 1e-9 else "良好" if score >= 0.8 else "合格" if score >= 0.6
            else "待改进" if score >= 0.4 else "不合格")


# ───────────────────────── 指标与评分(纯计算,不连 OSIS) ─────────────────────────

def metrics(data: dict) -> dict:
    """求解结果(SI 单位)→ 关键指标(kN、kN·m、MPa、mm)。data 的键见 _solve。"""
    xyz = {n[0]: n[1:] for n in data["nodes"]}
    girder, girder_nodes = set(), set()  # 主梁:沿桥向的梁单元(桥墩近竖直,弹簧两端同 x)
    for no, i, j in data["elements"]:
        if i in xyz and j in xyz:
            dx, dz = abs(xyz[i][0] - xyz[j][0]), abs(xyz[i][2] - xyz[j][2])
            if dx > 1e-6 and dz <= 0.2 * dx:
                girder.add(no)
                girder_nodes |= {i, j}
    last = data["last"]
    total, dead = f"_合计_{last}", f"_恒载_{last}"
    out: dict = {}

    reactions: dict[int, float] = {}
    for r in data["support_reaction"]:
        if r["loadCase"] == total:
            reactions[r["no"]] = reactions.get(r["no"], 0.0) + r["fz"] / 1e3
    out["reaction_sum"] = sum(reactions.values())
    out["reactions"] = {no: round(v, 1) for no, v in sorted(reactions.items())}
    if data.get("weight"):
        out["weight"] = data["weight"] / 1e3
        out["weight_ratio"] = out["reaction_sum"] / out["weight"]

    xs = sorted({round(xyz[no][0], 2) for no in reactions if no in xyz})  # 支承桩号 → 最大跨
    span = max((b - a for a, b in zip(xs, xs[1:])), default=0.0)
    uz = [abs(r["uz"]) for r in data.get("displacement", []) if r["loadCase"] == dead and r["no"] in girder_nodes]
    if span > 0 and uz:
        out.update(span=span, deflection=max(uz) * 1e3, sag=max(uz) / span)

    my: dict[str, dict] = {total: {}, dead: {}}
    for r in data["element_force"]:
        if r["loadCase"] in my and r["ele"] in girder:
            my[r["loadCase"]][(r["ele"], r["node"])] = r["my"] / 1e3
    if my[dead]:
        key = max(my[dead], key=lambda k: abs(my[dead][k]))
        m_dead = my[dead][key]
        m_ps = my[total].get(key, 0.0) - m_dead  # 合计 - 恒载 = 预应力(含时变效应)
        out.update(balance_ele=key[0], m_dead=m_dead, m_ps=m_ps,
                   balance=-m_ps / m_dead if abs(m_dead) > 1e-6 else None)

    rows = [r for r in data.get("element_stress", []) if r["ele"] in girder]
    parts = {"final": [r for r in rows if r["loadCase"] == total], "stage": rows,
             "long": [r for r in data.get("long_stress", []) if r["ele"] in girder]}
    for key, part in parts.items():
        if part:
            hi, lo = max(part, key=lambda r: r["sxComp"]), min(part, key=lambda r: r["sxComp"])
            where = lambda r: f"{r['loadCase'][len('_合计_'):]} 单元 {r['ele']}"  # noqa: E731
            out[f"{key}_max"], out[f"{key}_max_at"] = hi["sxComp"] / 1e6, where(hi)
            out[f"{key}_min"], out[f"{key}_min_at"] = lo["sxComp"] / 1e6, where(lo)
    return out


def judge(m: dict, tier: str, grade: int | None, prestressed: bool = True) -> list[dict]:
    """指标 → 分项 [{dim, name, score, value, reason, advice}]。阈值来由见 评分说明.md「受力评分」。"""
    items = []

    def add(dim: str, score: float, value: str, reason: str = "", advice: str = "") -> None:
        items.append({"dim": dim, "name": DIMS[dim], "score": round(score, 3), "value": value,
                      "reason": reason if score < 0.9 else "", "advice": advice if score < 0.9 else ""})

    if prestressed and grade:
        add("D1", 1.0 if grade >= 40 else 0.0, f"C{grade}", "预应力混凝土构件不应低于 C40(JTG 3362-2018 第 3.1.2 条)",
            "核对主梁混凝土材料的等级")
    if prestressed:
        b = m.get("balance")
        if b is None:
            add("D2", 0.0, "算不出", "主梁恒载弯矩为零或没有内力结果", "检查自重工况是否在施工阶段里激活、主梁单元是否激活")
        else:
            add("D2", lerp(-b, -0.8, -0.5),
                f"{b:.2f}(单元 {m['balance_ele']}:预应力弯矩 {m['m_ps']:.0f} kN·m,恒载弯矩 {m['m_dead']:.0f} kN·m)",
                f"预应力只抵消了恒载弯矩的 {b:.0%},正常不低于 80%",
                "检查钢束:预应力工况是否在施工阶段里激活、张拉控制应力、钢束根数与束数、钢束线形是否偏到了截面另一侧")

    negative = {no: v for no, v in m["reactions"].items() if v < -0.01 * max(abs(x) for x in m["reactions"].values())} \
        if m["reactions"] else {}
    if not m["reactions"] or m["reaction_sum"] <= 0:
        add("D3", 0.0, f"竖向合计 {m['reaction_sum']:.0f} kN", "没有竖向反力", "检查边界组和自重工况是否在施工阶段里激活")
    else:
        add("D3", 0.5 if negative else 1.0, f"竖向合计 {m['reaction_sum']:.0f} kN;各支承节点 {m['reactions']}",
            f"恒载+预应力下节点 {sorted(negative)} 出现负反力(支座脱空)", "检查边跨与中跨比例、支座位置和约束方向")

    if "weight_ratio" in m:
        r = m["weight_ratio"]
        add("D4", min(lerp(-r, -0.95, -0.7), lerp(r, 2.2, 2.8)),
            f"竖向反力合计 ÷ 结构自重 = {r:.2f}(反力 {m['reaction_sum']:.0f} kN,按截面面积×容重×长度估算的自重 {m['weight']:.0f} kN)",
            "反力比结构自重还小:自重没加全" if r < 1.0 else "反力远大于结构自重:自重或二期恒载可能重复计",
            "检查自重工况是否激活且只有一个、容重、二期恒载的量级和单位")
    if "sag" in m:
        s = m["sag"]
        add("D5", min(lerp(s, 1 / 250, 1 / 100), lerp(-s, -1 / 20000, -1 / 100000)),
            f"恒载挠度 {m['deflection']:.1f} mm,最大跨 {m['span']:.1f} m,挠跨比 1/{1 / s:.0f}" if s > 0 else "恒载下没有挠度",
            "恒载挠度过大:刚度偏小" if s > 1 / 250 else "恒载挠度过小:刚度偏大或恒载没加上",
            "检查混凝土弹性模量、截面尺寸的单位和量级、截面是否赋给了正确的单元")

    def stress(dim: str, key: str, t0: float, t1: float, c0: float, c1: float, when: str, advice: str) -> None:
        if f"{key}_max" not in m:
            return
        tens, comp = m[f"{key}_max"], -m[f"{key}_min"]
        ts, cs = lerp(tens, t0, t1), lerp(comp, c0, c1)
        add(dim, min(ts, cs),
            f"最大拉应力 {tens:.2f} MPa({m[f'{key}_max_at']}),限值 {t0:.2f};"
            f"最大压应力 {comp:.2f} MPa({m[f'{key}_min_at']}),限值 {c0:.1f}",
            f"{when}拉应力超限" if ts <= cs else f"{when}压应力超限", advice)

    fck, ftk = STRENGTH.get(grade, (None, None))
    if fck and tier in ("stage", "full"):
        stress("D6", "final", 0.0, 0.7 * ftk, 0.5 * fck, 0.7 * fck, "成桥(恒载+预应力,未计活载)",
               "拉应力超限:加大该处预应力,或检查该处钢束是否漏布、线形是否正确;压应力超限:减小预应力或加大截面")
        stress("D7", "stage", 1.15 * ftk, 2.0 * ftk, 0.7 * fck, 0.9 * fck, "施工阶段",
               "检查该阶段的钢束张拉顺序、张拉力、临时荷载与支承")
    if fck and tier == "full":
        stress("D8", "long", 0.0, 0.7 * ftk, 0.5 * fck, 0.7 * fck, "徐变十年后(恒载+预应力,未计活载)",
               "拉应力超限:预应力长期损失后储备不足,加大预应力;压应力超限:减小预应力或加大截面")
    return items


def report(name: str, tier: str, items: list[dict], info: dict) -> tuple[float, str]:
    overall = min(i["score"] for i in items)  # 取短板:一项不过,整体就不过
    lines = [f"# {name} 受力评分报告", "", "## 项目概况",
             f"- 档位:{TIERS[tier]}",
             f"- 评分维度:{'、'.join(i['dim'] for i in items)},共 {len(items)} 项",
             f"- 施工阶段:原 {info['stages']} 个,求解 {info['solved_stages']} 个;求解 {info['solve_s']} s",
             f"- 混凝土等级:{'C%d' % info['grade'] if info.get('grade') else '未读到'}",
             f"- 总分:{overall:.2f} / 1.0(各项取最低)", f"- 评级:{rating(overall)}", "", "## 分项检查"]
    for k, i in enumerate(items, 1):
        lines += ["", f"### {k}. {i['dim']} {i['name']}:{i['score']:.2f} / 1.0", f"- 结果:{i['value']}",
                  f"- 状态:{status(i['score'])}"]
        if i["reason"]:
            lines += [f"- 原因:{i['reason']}", f"- 建议:{i['advice']}"]
    if tier == "fast":
        lines += ["", "> 快速档不评应力(压成一个阶段后,有体系转换的桥应力不可信)。要看应力,用 `--tier stage` 再跑。"]
    lines += ["", "> 本报告只说明模型受力上没有大错。抗弯/抗剪承载力、活载下的抗裂要求解后用 osis-check 验算。"]
    return overall, "\n".join(lines)


# ───────────────────────── 第 2 步:求解器里跑 ─────────────────────────

def _solve(py: Path, tier: str, timeout: int) -> dict:
    """重建 py/prep/main.py 的模型,按档位改施工阶段,求解,取结果。"""
    import runpy

    from pyosis import OSISEngine
    from pyosis.core import command

    execute = command.OSISFunctionRegistry._execute_command

    def no_solve(self, cmd, timeout=None):  # 代码里自带的求解跳过:这里只要模型
        if cmd.split(",")[0].rstrip(";").lower() in ("solve", "combinesolve"):
            return True, ""
        return execute(self, cmd, timeout)

    command.OSISFunctionRegistry._execute_command = no_solve
    sys.path.insert(0, str(py / "prep"))
    try:
        runpy.run_path(str(py / "prep" / "main.py"), run_name="__main__")
    finally:
        command.OSISFunctionRegistry._execute_command = execute

    engine = OSISEngine()
    stages = sorted(engine.stage.all(), key=lambda s: s.no)
    keep = []  # 施工部分:徐变十年(时长 ≥ 1000 天)或带分析工况(活载/沉降)的阶段之前
    for s in stages:
        if s.duration >= 1000 or s.analysis_cases:
            break
        keep.append(s)
    if not keep:
        raise RuntimeError("没有可求解的施工阶段:第一个阶段就是徐变长期阶段或带活载/沉降分析")
    rest = stages[len(keep):]
    long = rest[0].name if rest and rest[0].duration >= 1000 else None  # 徐变十年阶段

    elements, boundaries, loads = {}, {}, {}
    for s in keep:  # 回放激活/钝化,得到成桥时还在的单元组、边界组、荷载工况
        for g in s.element_groups:
            elements[g.name] = g if g.activated else None
        for g in s.boundary_groups:
            boundaries[g.name] = g.activated
        for c in s.load_cases:
            loads[c.name] = c.activated

    # 结构自重估算:成桥时还在的单元,长度 × 两端截面平均面积 × 容重
    alive = set()
    for g in engine.element.group.all():
        if elements.get(g.name):
            alive |= set(g.elements)
    area = {s.no: (s.prop or {}).get("area") or 0.0 for s in engine.section.all()}
    unit_weight = {m.no: m.unit_weight or 0.0 for m in engine.material.all()}
    all_elements = engine.element.all()
    weight = sum(e.length * sum(area.get(s, 0.0) for s in e.sec_vec) / len(e.sec_vec) * unit_weight.get(e.mat, 0.0)
                 for e in all_elements if e.no in alive and e.sec_vec)

    last = keep[-1].name
    if tier == "stage":
        for s in reversed(rest):
            engine.stage.delete(s.no)
    elif tier == "fast":
        engine.stage.clear()
        one = engine.stage.create(1, "QUICK", 30.0)
        for name, g in elements.items():
            if g:
                one.define_element(1, 1, name, g.birth if g.birth is not None else 7.0, g.part or 0)
        for name, on in boundaries.items():
            if on:
                one.define_boundary(1, 1, name)
        gravity = False  # 自重工况作用在"本阶段激活的单元"上:压成一个阶段后只留一个,否则自重重复计
        for name, on in loads.items():
            if on:
                case = engine.load.get(name)
                if case is not None and case.gravity:
                    if gravity:
                        continue
                    gravity = True
                one.define_loadcase(1, 1, "", name)
        last = "QUICK"
    if tier != "full":  # 最后一个阶段的荷载被当成独立工况、不进累计:补一个空阶段收尾
        engine.stage.create(max(s.no for s in engine.stage.all()) + 1, "END", 0.0)

    t = time.time()
    engine.solve(timeout=timeout)
    data = {"last": last, "stages": len(stages), "solve_s": round(time.time() - t, 1), "weight": weight,
            "solved_stages": {"fast": 1, "stage": len(keep), "full": len(stages)}[tier],
            "nodes": [[n.no, n.x, n.y, n.z] for n in engine.node.all()],
            "elements": [[e.no, e.node_i, e.node_j] for e in all_elements]}
    names = [f"_合计_{last}", f"_恒载_{last}"]
    data["support_reaction"] = engine.result.support_reaction(names).to_dict("records")
    data["element_force"] = engine.result.element_force(names).to_dict("records")
    data["displacement"] = engine.result.node_displacement(names[1])[["loadCase", "no", "uz"]].to_dict("records")

    def stress(stage_name: str) -> list[dict]:  # 逐个取:哪张表没有表头,整次调用都会失败
        try:
            df = engine.result.element_stress(f"_合计_{stage_name}")
        except RuntimeError:
            return []
        return df[df["point"].isin(["Min", "Max"])].to_dict("records")

    data["element_stress"] = [r for s in keep for r in stress(s.name)] if tier != "fast" else []
    data["long_stress"] = stress(long) if tier == "full" and long else []
    return data


def run(args: argparse.Namespace) -> int:
    py = args.run
    try:
        data = _solve(py, args.tier, args.timeout)
    except Exception as exc:  # noqa: BLE001
        print(f"[error] 受力评分没算成: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    m = metrics(data)
    items = judge(m, args.tier, args.concrete_grade, args.is_prestressed)
    info = {k: data[k] for k in ("stages", "solved_stages", "solve_s")} | {"grade": args.concrete_grade}
    overall, text = report(args.name, args.tier, items, info)
    (py.parent / "mechanics.json").write_text(
        json.dumps({"overall": overall, "tier": args.tier, "items": items, "metrics": m, **info}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(text)
    print(f"\n>>> mechanics 总分: {overall:.4f}  (满分 1.0)")
    return 1 if overall < 0.5 else 0


# ───────────────────────── 第 1 步:准备;第 3 步:清理 ─────────────────────────

def _scratch(args: argparse.Namespace) -> tuple[Path, str]:
    """(临时目录, 工程名)。缺省放在工程目录下的 _mechanics/,和工程同盘。"""
    if args.candidate_dir is not None:
        project = args.candidate_dir.resolve().parent
    elif args.cleanup and args.scratch is not None:
        return args.scratch, ""
    else:
        from pyosis import OSISEngine
        directory = OSISEngine().project.get_directory()
        if not directory and args.scratch is None:
            raise RuntimeError("当前实例没有工程目录,用 --scratch 指定临时目录")
        project = Path(directory) if directory else args.scratch
    return (args.scratch or project / "_mechanics"), project.name


def _clean(scratch: Path) -> None:
    shutil.rmtree(scratch / "model", ignore_errors=True)  # 只删自己建的,不动 scratch 里别的东西
    for path in scratch.glob("model.sis*"):
        path.unlink(missing_ok=True)


def prepare(args: argparse.Namespace) -> int:
    from model_conformance.common import _scan_concrete_grade, collect_python_files

    try:
        scratch, name = _scratch(args)
        _clean(scratch)
        model = scratch / "model"
        if args.candidate_dir is not None:
            if not (args.candidate_dir / "prep" / "main.py").is_file():
                print("[error] --candidate-dir 要给 py/ 目录(下有 prep/main.py)", file=sys.stderr)
                return 2
            shutil.copytree(args.candidate_dir / "prep", model / "py" / "prep",
                            ignore=shutil.ignore_patterns("__pycache__"))
        else:
            from test_conformance import _export_model
            _export_model(model)
    except Exception as exc:  # noqa: BLE001
        print(f"[error] 准备临时工程失败: {type(exc).__name__}: {exc};先确认模型已写回 OSIS(跑过 prep/main.py)",
              file=sys.stderr)
        return 2
    grade = args.concrete_grade or _scan_concrete_grade(collect_python_files(model / "py"))
    argv = [str(Path(__file__).resolve()), "--run", str(model / "py"), "--tier", args.tier, "--name", name,
            "--timeout", str(args.timeout), "--is-prestressed", str(args.is_prestressed)]
    if grade:
        argv += ["--concrete-grade", str(grade)]
    launcher = model / "py" / LAUNCHER
    launcher.write_text(f"import runpy\nimport sys\n\nsys.argv = {argv!r}\nrunpy.run_path(sys.argv[0], run_name='__main__')\n",
                        encoding="utf-8")
    print(f"[info] 临时工程: {model}(混凝土等级 {'C%d' % grade if grade else '未读到'})")
    print(f"[next] 用 execute_python 跑第 2 步: instance_id=\"solver\", file=r\"{launcher}\", "
          f"cwd=r\"{launcher.parent}\", timeout={args.timeout}")
    print(f"[next] 读完报告后清理: test_mechanics.py --cleanup --scratch \"{scratch}\"")
    return 0


def _bool(text: str) -> bool:
    if text.strip().lower() in ("1", "true", "yes", "y", "是"):
        return True
    if text.strip().lower() in ("0", "false", "no", "n", "否"):
        return False
    raise argparse.ArgumentTypeError(f"无法解析 bool 值: {text!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="桥梁受力评分(mechanics)")
    parser.add_argument("--tier", choices=list(TIERS), default="fast", help="fast 快速档(缺省)/ stage 施工阶段档 / full 完整档")
    parser.add_argument("--candidate-dir", type=Path, default=None, help="读代码模式:工程 py/ 目录;缺省导出 OSIS 当前模型")
    parser.add_argument("--scratch", type=Path, default=None, help="临时目录;缺省 <工程目录>/_mechanics")
    parser.add_argument("--concrete-grade", type=int, default=None, help="主梁混凝土等级(如 50);缺省取模型里最高的")
    parser.add_argument("--is-prestressed", type=_bool, default=True, help="是否预应力结构(缺省 true);false 时不评 D1、D2")
    parser.add_argument("--timeout", type=int, default=3600, help="求解超时秒数(缺省 3600,execute_python 的上限)")
    parser.add_argument("--cleanup", action="store_true", help="删除临时工程后退出")
    parser.add_argument("--run", type=Path, default=None, help=argparse.SUPPRESS)  # 第 2 步,由启动脚本传
    parser.add_argument("--name", default="OSIS 当前模型", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.run is not None:
        return run(args)
    if args.cleanup:
        try:
            scratch, _ = _scratch(args)
        except Exception as exc:  # noqa: BLE001
            print(f"[error] {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
        _clean(scratch)
        print(f"[info] 已清理 {scratch / 'model'}")
        return 0
    return prepare(args)


if __name__ == "__main__":
    raise SystemExit(main())
