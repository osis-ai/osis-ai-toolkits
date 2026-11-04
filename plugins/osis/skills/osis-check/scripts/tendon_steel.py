"""按 py/prep 代码统计钢束用量：每类钢束的规格、束数、钢绞线根数、用钢量，并列出被多类钢束共用的规格。

    python tendon_steel.py                     # 默认读 <项目目录>/py/prep
    python tendon_steel.py --prep D:\\proj\\py\\prep

类别取形状名开头的字母（F0-1 → F，BB10-y → BB）。长度按控制点折线计，竖弯曲线只算 x-z 平面。
优化前后各跑一次，对比两次的输出。
"""

from __future__ import annotations

import argparse
import ast
import math
import re
from collections import defaultdict
from pathlib import Path

# GB/T 5224-2014 钢绞线每米重量 kg/m，按公称直径 mm
UNIT_WEIGHT = {15.2: 1.101, 12.7: 0.775, 17.8: 1.500, 21.6: 2.205}


def _val(node):
    try:
        return ast.literal_eval(node)
    except ValueError:
        return None


def _arg(call: ast.Call, idx: int, kw: str):
    for k in call.keywords:
        if k.arg == kw:
            return _val(k.value)
    return _val(call.args[idx]) if len(call.args) > idx else None


def _prop(call: ast.Call, fn: str) -> tuple[int, float]:
    """返回 (每束根数, 每束每米重量 kg/m)。直接给面积(m²)的写法按 15.2 钢绞线折根数。"""
    if fn == "create_in_custom" or (fn == "create" and _arg(call, 3, "area") == 0):
        area = _arg(call, 2, "val") if fn == "create_in_custom" else _arg(call, 4, "val")
        return round(area / 140e-6), area * 7850
    pos = (6, 5) if fn == "create" else (4, 3)  # (num, diameter) 的位置参数下标
    num, dia = _arg(call, pos[0], "num"), _arg(call, pos[1], "diameter")
    return num, num * UNIT_WEIGHT[float(dia)]


def parse_prep(prep: Path):
    props, curves, shapes = {}, {}, []
    for py in sorted(prep.glob("*.py")):
        for call in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)):
                continue
            owner, fn = ast.unparse(call.func.value), call.func.attr
            if owner.endswith("tendon.prop") and fn in ("create", "create_in", "create_in_custom"):
                props[_arg(call, 0, "name")] = _prop(call, fn)
            elif fn.startswith("create_arc") and len(call.args) >= 3 and _val(call.args[1]) == "TENDON":
                v = _val(call.args[2])
                if v is None:
                    continue
                k = 3 if fn == "create_arc2d" else 4  # 每点 (x, z, R) 或 (x, y, z, R)
                pts = [v[i:i + k - 1] for i in range(0, len(v), k)]
                curves[_val(call.args[0])] = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
            elif owner.endswith("tendon.shape") and fn.startswith("create") and len(call.args) >= 5:
                rest = [_val(a) for a in call.args[4:]]
                shapes.append((_val(call.args[0]), _val(call.args[1]), _val(call.args[2]), rest))
    return props, curves, shapes


def summarize(prep: Path):
    props, curves, shapes = parse_prep(prep)
    rows = defaultdict(lambda: {"规格": set(), "束数": 0, "根数": 0, "长度": 0.0, "用钢量": 0.0})
    users, missing = defaultdict(set), []
    for name, n_tendon, prop, rest in shapes:
        cls = re.match(r"[A-Za-z]*", name).group() or name
        curve = next((r for r in rest if isinstance(r, str) and r in curves), None)
        if curve is None or prop not in props:
            missing.append(name)
            continue
        num, kg_per_m = props[prop]
        n_tendon = n_tendon or 1
        r = rows[cls]
        r["规格"].add(prop)
        r["束数"] += n_tendon
        r["根数"] += n_tendon * num
        r["长度"] += n_tendon * curves[curve]
        r["用钢量"] += n_tendon * curves[curve] * kg_per_m / 1000
        users[prop].add(cls)
    shared = {p: sorted(c) for p, c in users.items() if len(c) > 1}
    return dict(rows), shared, missing


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--prep", help="默认 <项目目录>/py/prep")
    args = ap.parse_args()
    if args.prep:
        prep = Path(args.prep)
    else:
        from pyosis import OSISEngine
        prep = Path(OSISEngine().project.get_directory()) / "py" / "prep"

    rows, shared, missing = summarize(prep)
    total = sum(r["用钢量"] for r in rows.values())
    print("类别  规格            束数   根数   束长合计(m)  用钢量(t)  占比")
    for cls, r in sorted(rows.items()):
        print(f"{cls:<5} {'/'.join(sorted(r['规格'])):<14} {r['束数']:>5} {r['根数']:>6} {r['长度']:>12.1f} {r['用钢量']:>10.2f} {r['用钢量'] / total:>6.1%}")
    print(f"合计  {'':<14} {sum(r['束数'] for r in rows.values()):>5} {sum(r['根数'] for r in rows.values()):>6} "
          f"{sum(r['长度'] for r in rows.values()):>12.1f} {total:>10.2f}")
    for p, c in shared.items():
        print(f"共用规格 {p}: {', '.join(c)}（单改其中一类要新建规格）")
    if missing:
        print(f"未统计 {len(missing)} 个形状（曲线不是字面量或规格未找到）: {', '.join(missing[:10])}")


if __name__ == "__main__":
    main()
