# -*- coding: utf-8 -*-
"""把最接近的桥型模板整目录复制到当前 OSIS 项目 py/。

osis-engine 官方脚本,不是用户自定义插件。无参时把用法打到 stderr 并返回 1。

CLI:
  python seedtpl.py --spec "帮我建桥:变截面悬浇连续梁-65+120+65"
  python seedtpl.py "预制简支-空心板-16m-中梁"
  python seedtpl.py --spec "..." --dest D:\\proj --skills D:\\skills --dry-run
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

USAGE = """seedtpl 用法:

  python seedtpl.py --spec "<建桥描述或模板目录名>"
  python seedtpl.py --spec "帮我建桥:变截面悬浇连续梁-65+120+65"
  python seedtpl.py --spec "预制简支-空心板-16m-中梁" --dry-run

默认目标=当前 OSIS 工程 get_directory()/py/ 。已有 prep/*.py 时拒绝覆盖(加 --force)。
"""

BRIDGES: list[tuple[str, tuple[str, ...]]] = [
    ("osis-bridge-rigid-frame-box", ("刚构", "墩梁固结")),
    ("osis-bridge-hollow-slab", ("空心板",)),
    ("osis-bridge-precast-t-girder", ("T梁", "T 梁", "t梁")),
    ("osis-bridge-precast-small-box", ("小箱梁",)),
    ("osis-bridge-cantilever-box", ("悬浇", "悬臂浇筑", "悬臂", "变截面悬浇")),
    ("osis-bridge-conventional-box", ("现浇", "等截面箱梁", "常规箱梁", "变截面连续箱梁")),
]

# 允许 65 + 120 + 65m 这种空格/末尾 m；紧写 65+120+65 仍然命中。
PLUS_SPANS = re.compile(
    r"(?<![\d.])(\d+(?:\.\d+)?(?:\s*\+\s*\d+(?:\.\d+)?)+)m?(?![\d.])",
    re.I,
)
SINGLE_M = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)m(?![+\d])", re.I)
SINGLE_CN = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)米")
WIDTH_TAIL = re.compile(r"(?:单箱[^-\d]+|连续箱梁|箱梁)-(\d+(?:\.\d+))(?:-\d+)?$")


@dataclass
class Query:
    spec: str
    skill: str | None = None
    spans: list[float] = field(default_factory=list)
    girder: str | None = None  # 中梁 / 边梁
    pier: str | None = None  # 双肢 / 单肢
    system: str | None = None  # 简支变连续 / 预制简支
    box: str | None = None
    width: float | None = None


@dataclass
class Template:
    name: str
    path: Path
    skill: str
    spans: list[float] = field(default_factory=list)
    girder: str | None = None
    pier: str | None = None
    system: str | None = None
    box: str | None = None
    width: float | None = None


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconf = getattr(stream, "reconfigure", None)
        if reconf is not None:
            try:
                reconf(encoding="utf-8")
            except Exception:
                pass


def parse_spans(text: str) -> list[float]:
    m = PLUS_SPANS.search(text)
    if m:
        return [float(x.strip()) for x in m.group(1).split("+") if x.strip()]
    m = SINGLE_M.search(text) or SINGLE_CN.search(text)
    if m:
        return [float(m.group(1))]
    return []


def parse_girder(text: str) -> str | None:
    if "中梁" in text:
        return "中梁"
    if "边梁" in text:
        return "边梁"
    return None


def parse_pier(text: str) -> str | None:
    if "双肢" in text:
        return "双肢"
    if "单肢" in text:
        return "单肢"
    return None


def parse_system(text: str) -> str | None:
    if "简支变连续" in text:
        return "简支变连续"
    if "预制简支" in text:
        return "预制简支"
    return None


def parse_box(text: str) -> str | None:
    for token in ("单箱多室", "单箱双室", "单箱单室"):
        if token in text:
            return token
    return None


def parse_width(text: str) -> float | None:
    m = WIDTH_TAIL.search(text)
    if m:
        return float(m.group(1))
    return None


def route_skill(text: str) -> str | None:
    for skill, keys in BRIDGES:
        if any(k in text for k in keys):
            return skill
    return None


def parse_query(spec: str, skill: str | None = None) -> Query:
    text = spec.strip()
    text = re.sub(r"^帮我建桥\s*[:：]?", "", text).strip()
    q = Query(spec=text)
    q.skill = skill or route_skill(text)
    q.spans = parse_spans(text)
    q.girder = parse_girder(text)
    q.pier = parse_pier(text)
    q.system = parse_system(text)
    q.box = parse_box(text)
    q.width = parse_width(text)
    return q


def parse_template(path: Path, skill: str) -> Template:
    name = path.name
    return Template(
        name=name,
        path=path,
        skill=skill,
        spans=parse_spans(name),
        girder=parse_girder(name),
        pier=parse_pier(name),
        system=parse_system(name),
        box=parse_box(name),
        width=parse_width(name),
    )


def discover_skill_roots(explicit: Path | None) -> list[Path]:
    roots: list[Path] = []

    def add(raw: str | Path | None) -> None:
        if not raw:
            return
        p = Path(raw)
        if p.name != "skills":
            cand = p / "skills"
            if cand.is_dir():
                p = cand
        if p.is_dir() and p not in roots:
            roots.append(p)

    add(explicit)
    add(os.environ.get("OPENCODE_SKILLS_DIR"))
    add(os.environ.get("OSIS_EXTRA_CONFIG_DIR"))
    add(os.environ.get("OPENCODE_CONFIG_DIR"))
    here = Path(__file__).resolve()
    for anc in here.parents:
        if anc.name == "skills" and (anc / "osis-engine").is_dir():
            add(anc)
            break
        if (anc / "skills").is_dir() and (anc / "plugins").is_dir():
            add(anc / "skills")
            break
    add(Path.home() / ".osisai" / ".agents" / "skills")
    return roots


def resolve_skill_dir(skill: str, roots: list[Path]) -> Path | None:
    for root in roots:
        cand = root / skill
        if (cand / "SKILL.md").is_file() and (cand / "references" / "templates").is_dir():
            return cand
    return None


def list_templates(skill: str, roots: list[Path]) -> list[Template]:
    skill_dir = resolve_skill_dir(skill, roots)
    if skill_dir is None:
        return []
    base = skill_dir / "references" / "templates"
    out: list[Template] = []
    for child in sorted(base.iterdir(), key=lambda p: p.name):
        if child.is_dir() and (child / "prep").is_dir():
            out.append(parse_template(child, skill))
    return out


def compatible(q: Query, t: Template) -> bool:
    if q.girder and t.girder and q.girder != t.girder:
        return False
    if q.pier and t.pier and q.pier != t.pier:
        return False
    if q.system and t.system and q.system != t.system:
        return False
    if q.box and t.box and q.box != t.box:
        return False
    return True


def span_key(q: Query, t: Template) -> tuple[int, float]:
    qs, ts = q.spans, t.spans
    if qs and ts and qs == ts:
        return (0, 0.0)
    if not qs or not ts:
        return (2, 999.0)
    if len(qs) == len(ts):
        l2 = sum((a - b) ** 2 for a, b in zip(qs, ts)) ** 0.5
        return (1, l2)
    return (
        2,
        abs(max(qs) - max(ts))
        + abs(sum(qs) - sum(ts))
        + 50 * abs(len(qs) - len(ts)),
    )


def score(q: Query, t: Template) -> tuple:
    exact_name = 0 if q.spec == t.name or q.spec.endswith(t.name) else 1
    span_rank, span_dist = span_key(q, t)
    width_pen = 0.0
    if q.width is not None and t.width is not None:
        width_pen = abs(q.width - t.width)
    girder_pen = 0 if (not q.girder or q.girder == t.girder) else 1
    return (exact_name, span_rank, span_dist, girder_pen, width_pen, t.name)


def pick_template(q: Query, templates: list[Template]) -> tuple[Template | None, str]:
    if not templates:
        return None, "未命中"
    pool = [t for t in templates if compatible(q, t)] or templates
    best = min(pool, key=lambda t: score(q, t))
    exact_name, span_rank, _, _, _, _ = score(q, best)
    if exact_name == 0:
        return best, "精确命中"
    return best, "近似命中"


def default_dest() -> Path:
    try:
        from pyosis import OSISEngine

        raw = OSISEngine().project.get_directory() or ""
    except Exception as e:
        raise RuntimeError(f"无法读取当前 OSIS 工程目录: {e}") from e
    if not str(raw).strip():
        raise RuntimeError("当前没有打开的 OSIS 工程(get_directory 为空)")
    return Path(raw)


def prep_occupied(prep: Path) -> bool:
    if not prep.is_dir():
        return False
    return any(p.suffix.lower() == ".py" for p in prep.iterdir() if p.is_file())


def copy_template(src: Path, dest_project: Path, force: bool) -> list[str]:
    prep_src = src / "prep"
    if not prep_src.is_dir():
        raise RuntimeError(f"模板没有 prep/: {src}")
    py_dst = dest_project / "py"
    prep_dst = py_dst / "prep"
    if prep_occupied(prep_dst) and not force:
        raise RuntimeError(
            f"目标已有模型文件,拒绝覆盖: {prep_dst} (覆盖请加 --force)"
        )
    if prep_dst.exists():
        shutil.rmtree(prep_dst)
    py_dst.mkdir(parents=True, exist_ok=True)
    shutil.copytree(prep_src.resolve(), prep_dst)
    copied = [str(prep_dst)]
    portrait = src / "项目画像.md"
    if portrait.is_file():
        dst_p = py_dst / "项目画像.md"
        shutil.copy2(portrait.resolve(), dst_p)
        copied.append(str(dst_p))
    return copied


def format_spans(spans: list[float]) -> str:
    if not spans:
        return "-"
    def fmt(x: float) -> str:
        return str(int(x)) if x == int(x) else str(x)

    return "+".join(fmt(x) for x in spans)


def run(ns: argparse.Namespace) -> int:
    spec = (ns.spec or "").strip()
    if not spec:
        print(USAGE, file=sys.stderr)
        return 1
    roots = discover_skill_roots(Path(ns.skills) if ns.skills else None)
    q = parse_query(spec, ns.bridge)
    if not q.skill:
        print("错误: 无法从描述判断桥型,请加 --bridge osis-bridge-...", file=sys.stderr)
        return 1
    templates = list_templates(q.skill, roots)
    names = [t.name for t in templates]
    chosen, kind = pick_template(q, templates)
    lines = [
        f"查库: {q.skill} 共 {len(templates)} 个模板: {names}",
        f"匹配: {kind}",
    ]
    if chosen is None:
        print("\n".join(lines), file=sys.stderr)
        print("错误: 该桥型模板库为空或找不到 skill", file=sys.stderr)
        return 1
    lines.append(f"模板: {chosen.name}")
    lines.append(f"源: {chosen.path}")
    lines.append(f"跨径: 模板 {format_spans(chosen.spans)} → 目标 {format_spans(q.spans)}")
    if ns.dry_run:
        lines.append("动作: dry-run,未复制")
        print("\n".join(lines))
        return 0
    dest = Path(ns.dest) if ns.dest else default_dest()
    dest = dest.resolve()
    copied = copy_template(chosen.path, dest, force=ns.force)
    lines.append(f"目标: {dest / 'py'}")
    for p in copied:
        lines.append(f"已复制: {p}")
    if kind == "精确命中":
        lines.append(f"下一步: python {dest / 'py' / 'prep' / 'main.py'}")
    else:
        lines.append(
            "下一步: 悬浇三跨只改跨径 → python "
            f"{Path(__file__).with_name('spanremap.py')} --to <目标跨径>; "
            "其余按桥型 SKILL 最小 diff,再 python "
            f"{dest / 'py' / 'prep' / 'main.py'}"
        )
    lines.append("请只改当前 OSIS 工程 py/prep,不要手抄到其它目录。")
    print("\n".join(lines))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="seedtpl",
        description="把最接近的桥型模板复制到当前 OSIS 项目 py/",
        add_help=True,
    )
    p.add_argument("spec", nargs="?", default="", help="建桥描述或模板目录名")
    p.add_argument("--spec", dest="spec_opt", default="", help="同上,与位置参数二选一")
    p.add_argument("--bridge", default="", help="桥型 skill 名,可省略")
    p.add_argument("--dest", default="", help="工程根目录,默认 get_directory()")
    p.add_argument("--skills", default="", help="skills 根目录")
    p.add_argument("--force", action="store_true", help="覆盖已有 py/prep")
    p.add_argument("--dry-run", action="store_true", help="只匹配不复制")
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
    ns.spec = (ns.spec_opt or ns.spec or "").strip()
    ns.bridge = ns.bridge.strip() or None
    ns.dest = ns.dest.strip() or None
    ns.skills = ns.skills.strip() or None
    try:
        return run(ns)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
