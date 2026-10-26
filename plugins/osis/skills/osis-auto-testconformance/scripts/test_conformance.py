"""构造正确性 CLI:对 OSIS 里的模型跑 model_conformance,出总分 + 分项报告。

评的是模型,不是代码:OSIS 当前实例的模型用 export_apdl 导出求解器命令流,pyosis.transfer 转回模板结构的
prep 代码(临时目录,不碰工程),再按桥型规则评分。代码怎么写(变量、循环、辅助函数、另一种 API)不影响得分。
桥型/连续性应由调用方(建模 AI)显式传入;主跨 L 从节点/支座几何提取,不从目录名猜。

用法:

    # 1. 标准模式:评 OSIS 当前模型,显式传桥型(推荐)
    python test_conformance.py --bridge-type cantilever_box --is-continuous true

    # 2. 读代码模式:没有 OSIS 时评一个工程的代码(如模板);代码须与模型一致,结果才可信
    python test_conformance.py --candidate-dir <py 目录> --bridge-type cantilever_box --is-continuous true

参数:
    --candidate-dir PATH    读代码模式:工程的 py/ 目录(或模板目录,下有 prep/);缺省评 OSIS 当前模型
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
import shutil
import sys
import tempfile
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


def _export_model(out: Path) -> str:
    """OSIS 当前模型 → out/OSIS.out(求解器命令流)→ out/py/prep(pyosis.transfer 转回的代码)。返回工程名。"""
    from pyosis import OSISEngine
    from pyosis.transfer.out_to_python import write_prep_outputs

    engine = OSISEngine()
    prep = out / "py" / "prep"
    prep.mkdir(parents=True, exist_ok=True)  # OSIS 不自己建目录
    engine.export_apdl(str(out / "OSIS.out"))
    write_prep_outputs(out / "OSIS.out", prep)
    project = engine.project.get_directory()
    return Path(project).name if project else "OSIS 当前模型"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="桥梁构造建模正确性评测(model_conformance)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--candidate-dir", type=Path, default=None,
                        help="读代码模式:工程 py/ 目录;缺省评 OSIS 当前模型")
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

    if args.candidate_dir is not None:
        return _run(args, args.candidate_dir)
    tmp = Path(tempfile.mkdtemp(prefix="conformance-"))
    try:
        try:
            name = _export_model(tmp)
        except Exception as exc:  # noqa: BLE001
            print(f"[error] 导出 OSIS 当前模型失败: {type(exc).__name__}: {exc};"
                  "先确认模型已写回 OSIS(跑过 prep/main.py);没有 OSIS 时用 --candidate-dir 读代码",
                  file=sys.stderr)
            return 2
        print(f"[info] 评 OSIS 当前模型: {name}", file=sys.stderr)
        return _run(args, tmp / "py", name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _run(args: argparse.Namespace, candidate_dir: Path, name: str | None = None) -> int:
    # 1. 候选目录;读代码模式指向 py/ 时取上一级项目目录名,否则取目录自身名
    if name is None:
        name = candidate_dir.parent.name if candidate_dir.name == "py" else candidate_dir.name
    if not candidate_dir.is_dir():
        print(f"[error] 候选目录不存在: {candidate_dir}", file=sys.stderr)
        return 2
    if candidate_dir.name == "prep":  # 规则按 prep/_N_xxx.py 认模块,给 prep/ 本身会全部读空
        print("[error] --candidate-dir 要给 py/ 目录(下有 prep/),不是 prep/ 本身", file=sys.stderr)
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
