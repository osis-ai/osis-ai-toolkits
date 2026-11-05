# -*- coding: utf-8 -*-
"""计算书插件后端:按本目录固化的模板与映射,为当前打开的 OSIS 项目生成计算书。

由 osis-calcbook 打包生成,目录里有:
  模板 .docx(唯一一个)、mapping.json(填写映射)、docx_fill.py、data.py、ui.tsx(界面)、本文件

    python main.py [-o 输出.docx]     默认输出到项目根目录 计算书_<模板名>.docx,重名自动加序号

进度逐行打到 stdout,最后一行是 JSON:{"output": 计算书路径, "report": 填写报告}。
前提:OSIS 已打开项目并完成验算。
"""
import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def find_template() -> Path:
    docs = [p for p in HERE.glob("*.docx") if not p.name.startswith("~$")]
    if len(docs) != 1:
        raise RuntimeError(f"插件目录里应只有一个模板 .docx,现在有 {len(docs)} 个:{HERE}")
    return docs[0]


def project_dir() -> Path:
    try:
        from pyosis.project import get_project_directory
        d = get_project_directory()
    except Exception as e:
        raise RuntimeError(f"连不上 OSIS,请先打开 OSIS 和项目:{e}")
    if not d or not Path(d).is_dir():
        raise RuntimeError(f"OSIS 没有返回有效的项目目录:{d!r}")
    return Path(d)


def free_name(path: Path) -> Path:
    n = 1
    out = path
    while out.exists():
        out = path.with_name(f"{path.stem}_{n}{path.suffix}")
        n += 1
    return out


def generate(output: str | None) -> dict:
    import docx_fill

    template = find_template()
    proj = project_dir()
    print(f"项目目录:{proj}", flush=True)
    checks = list((proj / "Check").glob("*.txt")) if (proj / "Check").is_dir() else []
    if not checks:
        raise RuntimeError("当前项目还没有验算结果,请先在 OSIS 中完成验算再生成计算书")

    print("导出 OSIS 数据…", flush=True)
    r = subprocess.run([sys.executable, str(HERE / "data.py"), "-o", "项目数据结构.json"],
                       cwd=proj, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode != 0 or not (proj / "项目数据结构.json").is_file():
        raise RuntimeError(f"导出数据失败:\n{r.stdout}\n{r.stderr}")

    out = Path(output) if output else free_name(proj / f"计算书_{template.stem}.docx")
    print(f"按模板生成:{template.name}", flush=True)
    buf_out, buf_err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
        try:
            code = docx_fill.apply(str(template), str(HERE / "mapping.json"), str(out), proj)
        except PermissionError:
            raise RuntimeError(f"写不进 {out},文件可能正在 Word 里打开")
    if code != 0:
        raise RuntimeError(f"映射与模板不匹配,请让 OSIS-AI 修复插件:\n{buf_err.getvalue()}")
    # 只给用户看结果和占位清单;"未处理段落"是编写映射时用的
    report = buf_out.getvalue().split("\n未处理且含数字")[0].strip()
    return {"output": str(out), "report": report}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="为当前 OSIS 项目生成计算书")
    parser.add_argument("-o", "--output", help="输出 .docx 路径,默认项目根目录 计算书_<模板名>.docx")
    ns = parser.parse_args()
    try:
        res = generate(ns.output)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
