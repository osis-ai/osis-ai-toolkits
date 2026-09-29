"""构造正确性 CLI:对候选代码跑 model_conformance,出总分 + 分项报告。

桥型/连续性应由调用方(建模 AI)显式传入;主跨 L 从节点/支座几何提取,不从目录名猜。

用法(以下三选一,推荐第 1 种):

    # 1. 标准模式:显式传桥型(推荐)
    python test_conformance.py \
        --candidate-dir <path> \
        --bridge-type cantilever_box \
        --is-continuous true

    # 2. 只指定候选目录(桥型从目录名猜,猜不中回退 unknown)
    python test_conformance.py --candidate-dir <path>

    # 3. 自动模式:从 OSIS 当前项目读 py/(桥型从目录名猜)
    python test_conformance.py

参数:
    --candidate-dir PATH    候选代码目录(含 *.py)
    --bridge-type TYPE      cantilever_box / rigid_frame / t_girder /
                            precast_small_box / cast_in_place_box /
                            hollow_slab / unknown
    --expected-L FLOAT      可选;仅当节点提取不到主跨时作兜底
    --is-continuous BOOL    是否连续梁;缺省从目录名解析
    --is-prestressed BOOL   是否预应力(可选)
    --concrete-ratio FLOAT  混凝土折算厚度 m³/m²(可选)
    --beam-width FLOAT      桥宽 m(可选)
    --output PATH           报告写到文件;缺省打印到 stdout
    --no-auto-detect        桥型识别不出时报错,不用 unknown 兜底
    --list-bridge-types     列出支持的桥型并退出
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 把当前目录加进 sys.path,让 model_conformance 能平铺导入
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from model_conformance import (
    collect_python_files,
    detect_bridge_type,
    generate_report,
    _score_one,
)


SUPPORTED_BRIDGE_TYPES = [
    "cantilever_box",
    "rigid_frame",
    "t_girder",
    "precast_small_box",
    "cast_in_place_box",
    "hollow_slab",
    "unknown",
]


def _parse_bool(s: str) -> bool:
    s = s.strip().lower()
    if s in ("1", "true", "yes", "y", "是"):
        return True
    if s in ("0", "false", "no", "n", "否"):
        return False
    raise argparse.ArgumentTypeError(f"无法解析 bool 值: {s!r}")


def _detect_project_dir() -> Path | None:
    """从 OSIS 当前项目读 py/。失败返 None。"""
    try:
        from pyosis import OSISEngine
        d = OSISEngine().project.get_directory()
        return Path(d) if d else None
    except Exception:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="桥梁构造建模正确性评测(model_conformance)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--candidate-dir", type=Path, default=None,
                        help="候选代码目录;缺省从 OSIS 当前项目读 py/")
    parser.add_argument("--bridge-type", choices=SUPPORTED_BRIDGE_TYPES, default=None,
                        help="桥型;缺省从目录名识别")
    parser.add_argument("--expected-L", type=float, default=None,
                        help="可选;仅当节点提取不到主跨时作兜底")
    parser.add_argument("--is-continuous", type=_parse_bool, default=None,
                        help="是否连续梁;缺省从目录名解析")
    parser.add_argument("--is-prestressed", type=_parse_bool, default=None,
                        help="是否预应力(可选)")
    parser.add_argument("--concrete-ratio", type=float, default=None,
                        help="混凝土折算厚度 m³/m²(可选)")
    parser.add_argument("--beam-width", type=float, default=None,
                        help="桥宽 m(可选)")
    parser.add_argument("--output", type=Path, default=None,
                        help="报告写到文件;缺省打印到 stdout")
    parser.add_argument("--no-auto-detect", action="store_true",
                        help="桥型/跨径识别不出时报错,不用 unknown 兜底")
    parser.add_argument("--list-bridge-types", action="store_true",
                        help="列出支持的桥型并退出")
    args = parser.parse_args(argv)

    if args.list_bridge_types:
        print("支持的桥型:")
        for t in SUPPORTED_BRIDGE_TYPES:
            print(f"  - {t}")
        return 0

    # 1. 定位候选目录
    candidate_dir = args.candidate_dir
    name = None
    if candidate_dir is None:
        project = _detect_project_dir()
        if project is None:
            print("[error] 拿不到 OSIS 项目目录;请 --candidate-dir 显式指定,"
                  "或先启动 OSIS 桌面端并打开项目", file=sys.stderr)
            return 2
        candidate_dir = project / "py"
        name = project.name
        print(f"[info] 用 OSIS 当前项目: {project}", file=sys.stderr)
    else:
        # 指向 py/ 时取上一级项目目录名;否则取目录自身名
        name = candidate_dir.parent.name if candidate_dir.name == "py" else candidate_dir.name

    if not candidate_dir.is_dir():
        print(f"[error] 候选目录不存在: {candidate_dir}", file=sys.stderr)
        return 2

    # 2. 桥型路由
    bridge_type = args.bridge_type
    if bridge_type is None:
        bridge_type = detect_bridge_type(name) if name else None
        if bridge_type is None:
            if args.no_auto_detect:
                print(f"[error] 桥型识别不出(目录名={name!r}),用 --bridge-type 显式指定",
                      file=sys.stderr)
                return 2
            bridge_type = "unknown"
            print(f"[warn] 桥型识别不出(目录名={name!r}),回退 unknown", file=sys.stderr)
        else:
            print(f"[info] 桥型: {bridge_type} (从目录名 {name!r})", file=sys.stderr)

    # 3. 跨径 / 连续性。主跨 L 由评分器从节点提取;--expected-L 仅作节点失败时的兜底。
    expected_L = args.expected_L

    is_continuous = args.is_continuous
    if is_continuous is None and name:
        is_continuous = "简支变连续" in name
        print(f"[info] 连续性: {is_continuous} (从目录名)", file=sys.stderr)

    # 4. 读候选
    files = collect_python_files(candidate_dir)
    if not files:
        print(f"[error] 候选目录里没找到 .py 文件: {candidate_dir}", file=sys.stderr)
        return 2

    # 5. 评分
    score_kwargs: dict = {
        "bridge_type": bridge_type,
        "expected_L": expected_L,
        "is_continuous": is_continuous,
    }
    if args.is_prestressed is not None:
        score_kwargs["is_prestressed"] = args.is_prestressed
    if args.concrete_ratio is not None:
        score_kwargs["concrete_ratio"] = args.concrete_ratio
    if args.beam_width is not None:
        score_kwargs["beam_width"] = args.beam_width

    overall, details = _score_one(files, **score_kwargs)

    # 6. 报告(generate_report 吃的是 evaluate 风格的结果 dict,candidate 键下才是 details)
    report = generate_report(
        {"candidate": details, "bridge_type": bridge_type},
        candidate_name=name or candidate_dir.name,
    )
    footer = f"\n>>> model_conformance 总分: {overall:.4f}  (满分 1.0)"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + footer, encoding="utf-8")
        print(f"[info] 报告写到: {args.output}", file=sys.stderr)
    else:
        print(report)
        print(footer)

    # 退出码:fail < 0.5 返非零,方便脚本判断
    return 1 if overall < 0.5 else 0


if __name__ == "__main__":
    raise SystemExit(main())