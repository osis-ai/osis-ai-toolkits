"""按当前模型生成 py/post/main.py：荷载组合 + 规范验算的 pyosis 代码（JTG，组合规则同 OSIS 5.1「自动组合与验算」）。

    python gen_post.py --construct Pre     # 预制梁：空心板、T 梁、小箱梁
    python gen_post.py --construct Cast    # 现浇：现浇箱梁、悬浇连续梁、连续刚构

模型须已重建（工况、活载工况、沉降组都在 OSIS 里），不必先求解。默认写到 <项目目录>/py/post/main.py（已有的覆盖）。
生成的是展开的 create_combine / add_to_combine / add_check 调用，可以直接改：增删组合、改系数、只验算部分单元。
工况、活载、沉降组改了以后要重新生成。
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path

from pyosis import OSISEngine

# 求解后自动生成的施工阶段合计结果。承载能力（基本组合）只计预应力二次效应
BASIC_PERMANENT = ("_恒载_", "_钢束二次_", "_收缩二次_", "_徐变二次_")
SERVICE_PERMANENT = ("_恒载_", "_钢束一次_", "_钢束二次_", "_收缩二次_", "_徐变二次_")
# (验算项, 用哪个包络)；MinMax 是施工阶段荷载包络。最后一行 GUI 自动验算也算，但它的 OSISPost.out 里不写
CHECKS = (("UltM", "基本组合包络"), ("UltN", "基本组合包络"), ("Shear", "基本组合包络"),
          ("SSNC", "标准组合包络"), ("SSPC", "标准组合包络"),
          ("CrackS", "频遇组合包络"), ("CrackWeb", "频遇组合包络"), ("CrackWidth", "频遇组合包络"),
          ("CrackL", "准永久组合包络_直接作用"), ("CSNC", "MinMax"), ("CSNT", "MinMax"), ("CrackL", "准永久组合包络"))


def impact(frequency: float) -> float:
    """冲击系数 μ，JTG D60-2015 4.3.2（f 为结构基频，Hz）"""
    if frequency < 1.5:
        return 0.05
    if frequency > 14:
        return 0.45
    return 0.1767 * math.log(frequency) - 0.0157


def read_model(engine: OSISEngine) -> dict:
    """组合要用的模型信息，都按模型顺序：工况 [名, 类型]、活载工况 [名, 冲击频率或 None=不计冲击]、沉降组名"""
    def frequency(case):
        # shortcut: 子工况取第一个的频率（模板里各子工况相同），子工况频率不同时要逐个确认 GUI 取哪个
        sub = case.sub_load_cases[0] if case.sub_load_cases else None
        return sub.mu_paras[0] if sub and sub.is_calc_mu and sub.mu_paras else None

    return {"loads": [[c.name, c.type_name] for c in engine.load.all()],
            "lives": [[c.name, frequency(c)] for c in engine.live.case.all()],
            "settles": [s.name for s in engine.settlement.all()]}


def combinations(loads: list, lives: list, settles: list) -> list[tuple[str, str, str, str, list[tuple[str, float]]]]:
    """[(组合名, 组合类型, ADD/OR, 说明, [(工况或组合名, 系数)])]，顺序、命名同 GUI 生成的 OSISPost.out"""
    temps = [name for name, kind in loads if kind == "T"]
    grads = [name for name, kind in loads if kind == "TG"]
    # GUI 按模型里活载工况的倒序展开。对称的左/右偏载 My 相同，包络取同一极值时排在前面的胜出，所以顺序会影响结果
    # shortcut: 倒序只在一个 3 活载工况模板（悬浇 30+50+30）上核对过，再遇到多活载工况模型时先和 GUI 对一下
    lives = [(name, 1 + impact(f) if f is not None else 1.0) for name, f in lives][::-1]
    pairs = list(itertools.product(temps or [None], grads or [None])) if temps or grads else []
    stl = "+{:.1f}*STL" if settles else ""
    out, n = [], 0

    def add(kind: str, label: str, prompt: str, members: list[tuple[str, float]]) -> None:
        nonlocal n
        n += 1
        out.append((f"{label}{n}", kind, "ADD", f"{label[:-2]}:{prompt}", members))

    def envelope(kind: str, label: str, names: list[str], suffix: str = "") -> None:
        prompt = "+".join(f"1.0*{x}" for x in names)
        out.append((f"{label}包络{suffix}", kind, "OR", f"{label[:-2]}{suffix}:{prompt}", [(x, 1.0) for x in names]))

    def temp_part(pair, t: float, tg: float) -> tuple[list[tuple[str, float]], str]:
        members = [(x, f) for x, f in zip(pair, (t, tg)) if x]
        return members, "".join(f"+{p}*{k}" for x, p, k in zip(pair, (_f(t), _f(tg)), ("T", "TG")) if x)

    # 基本组合：恒载与预应力同取不利 1.2 / 有利 1.0；可变作用 = 无、活载、温度、活载 + 0.75 温度
    first = n
    for g in (1.2, 1.0):
        perm = [(BASIC_PERMANENT[0], g), (BASIC_PERMANENT[1], g), (BASIC_PERMANENT[2], 1.0), (BASIC_PERMANENT[3], 1.0)]
        perm += [(s, 0.5) for s in settles]
        head = f"{g:.1f}*D+{g:.1f}*PS+1.0*SH+1.0*CR" + stl.format(0.5)
        add("Basic", "基本组合", head, perm)
        for live, _ in lives:
            add("Basic", "基本组合", head + "+1.4*L", perm + [(live, 1.4)])
        for pair in pairs:
            members, text = temp_part(pair, 1.4, 1.4)
            add("Basic", "基本组合", head + text, perm + members)
        for live, _ in lives:
            for pair in pairs:
                members, _ = temp_part(pair, 1.05, 1.05)
                text = "".join(f"+1.4*0.75*{k}" for x, k in zip(pair, ("T", "TG")) if x)
                add("Basic", "基本组合", head + "+1.4*L" + text, perm + [(live, 1.4)] + members)
    envelope("Basic", "基本组合", [c[0] for c in out[first:]])

    # 标准 / 频遇 / 准永久：永久作用系数 1.0；活载系数 ψ/(1+μ)，取三位小数（活载工况结果已含冲击）；没有只有永久作用的组合
    perm = [(x, 1.0) for x in SERVICE_PERMANENT] + [(s, 1.0) for s in settles]
    head = "1.0*D+1.0*PS+1.0*SH+1.0*CR" + stl.format(1.0)
    for kind, label, psi, t, tg in (("Standard", "标准组合", 1.0, 1.0, 1.0), ("Frequent", "频遇组合", 0.7, 1.0, 0.8),
                                    ("Quasipermanent", "准永久组合", 0.4, 1.0, 0.8)):
        first = len(out)
        for live, mu1 in lives:
            add(kind, label, head + f"+{_f(psi)}*L", perm + [(live, psi if psi == 1.0 else round(psi / mu1, 3))])
        direct = [c[0] for c in out[first:]]
        for pair in pairs:
            members, text = temp_part(pair, t, tg)
            add(kind, label, head + text, perm + members)
        for live, mu1 in lives:
            for pair in pairs:
                members, text = temp_part(pair, t, tg)
                add(kind, label, head + f"+{_f(psi)}*L" + text,
                    perm + [(live, psi if psi == 1.0 else round(psi / mu1, 3))] + members)
        envelope(kind, label, [c[0] for c in out[first:]])
        if kind == "Quasipermanent":  # 长期抗裂只用直接作用（不含温度）
            envelope(kind, label, direct, "_直接作用")
    return out


def _q(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def _f(x: float) -> str:
    return f"{x:.1f}" if round(x, 1) == x else f"{x:g}"


def render(name: str, model: dict, construct: str, member: str = "APC", tension: str = "Post") -> str:
    """一个工程的 post/main.py：展开的 pyosis 调用，求解后可单独运行"""
    lines = [f'"""{name} — 荷载组合与规范验算（JTG，组合规则同 OSIS 5.1「自动组合与验算」）。', "",
             "求解后运行。由 osis-check 的 scripts/gen_post.py 按本模型的工况生成；工况、活载、沉降组改了要重新生成。", '"""', "",
             "from pyosis import OSISEngine, batch", "", "",
             "def build_post(engine: OSISEngine) -> None:", "    post = engine.post", "", "    # 荷载组合",
             "    with batch():", '        post.delete_combines("All")']
    for combine, kind, op, prompt, members in combinations(model["loads"], model["lives"], model["settles"]):
        lines.append(f'        post.create_combine({_q(combine)}, "Env", "Concrete", {_q(kind)}, {_q(op)}, {_q(prompt)})')
        lines += [f"        post.add_to_combine({_q(combine)}, {_q(m)}, {factor:g})" for m, factor in members]
    lines += ["    post.solve_combines()", "", "    # 规范验算", "    with batch():", '        post.delete_checks("All")']
    lines += [f"        post.add_check({_q(item)}, {_q(combine)})" for item, combine in CHECKS]
    lines += ['    post.select_elements("All")  # 只验算部分单元时改这里，如 post.select_elements("S", "1to20")',
              f"    post.set_member_type({_q(member)}, {_q(construct)}, {_q(tension)})  # 构件类型、施工方式（Pre 预制 / Cast 现浇）、张拉方式",
              '    post.set_check_items("All")  # 只开部分验算项：post.set_check_items(\'[{"UltM":1,"Shear":1}]\')',
              "    post.solve_checks()", "", "",
              'if __name__ == "__main__":', "    from pyosis.core import set_timeout", "",
              "    set_timeout(10800)  # 大模型组合 + 验算超过 pyosis 默认的 3600 s", "    build_post(OSISEngine())", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--construct", choices=["Pre", "Cast"], required=True, help="Pre 预制梁 / Cast 现浇")
    parser.add_argument("--member", default="APC", choices=["EPC", "APC", "BPC"],
                        help="EPC 全预应力 / APC A 类（默认，一般梁桥）/ BPC B 类")
    parser.add_argument("--tension", default="Post", choices=["Pre", "Post"], help="Pre 先张 / Post 后张（默认）")
    parser.add_argument("--out", help="默认 <项目目录>/py/post/main.py")
    parser.add_argument("--name", help="写进文件说明的工程名，默认项目目录名")
    args = parser.parse_args()
    engine = OSISEngine()
    project = Path(engine.project.get_directory())
    out = Path(args.out) if args.out else project / "py" / "post" / "main.py"
    model = read_model(engine)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(args.name or project.name, model, args.construct, args.member, args.tension), encoding="utf-8")
    print(f"{out}: {len(model['loads'])} 个工况, {len(model['lives'])} 个活载工况, {len(model['settles'])} 个沉降组")


if __name__ == "__main__":
    main()
