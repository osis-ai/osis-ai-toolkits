# -*- coding: utf-8 -*-
"""计算书插件:按本目录固化的模板与映射,为当前打开的 OSIS 项目生成计算书。

由 osis-calcbook 打包生成,目录里有:
  模板 .docx(唯一一个)、mapping.json(填写映射)、docx_fill.py、data.py、本文件

GUI:  python main.py --ui
CLI:  python main.py [-o 输出.docx]     默认输出到项目根目录 计算书_<模板名>.docx,重名自动加序号

前提:OSIS 已打开项目并完成验算。
"""
import argparse
import contextlib
import io
import os
import subprocess
import sys
import threading
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


# ---- 核心逻辑:GUI 与 CLI 共用 ----
def generate(output: str | None, log) -> Path:
    import docx_fill

    template = find_template()
    proj = project_dir()
    log(f"项目目录:{proj}")
    checks = list((proj / "Check").glob("*.txt")) if (proj / "Check").is_dir() else []
    if not checks:
        raise RuntimeError("当前项目还没有验算结果,请先在 OSIS 中完成验算再生成计算书")

    log("导出 OSIS 数据…")
    r = subprocess.run([sys.executable, str(HERE / "data.py"), "-o", "项目数据结构.json"],
                       cwd=proj, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode != 0 or not (proj / "项目数据结构.json").is_file():
        raise RuntimeError(f"导出数据失败:\n{r.stdout}\n{r.stderr}")

    out = Path(output) if output else free_name(proj / f"计算书_{template.stem}.docx")
    log(f"按模板生成:{template.name}")
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
    log(report)
    return out


# ---- CLI ----
def run_cli(args: list[str]) -> int:
    parser = argparse.ArgumentParser(description="为当前 OSIS 项目生成计算书")
    parser.add_argument("-o", "--output", help="输出 .docx 路径,默认项目根目录 计算书_<模板名>.docx")
    ns = parser.parse_args(args)
    try:
        generate(ns.output, print)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    return 0


# ---- GUI ----
def run_gui() -> None:
    import customtkinter as ctk

    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    try:
        name = find_template().stem
    except Exception:
        name = "计算书"
    root.title(f"生成计算书 — {name}")
    root.geometry("640x420")

    ctk.CTkLabel(root, text="为当前打开的 OSIS 项目生成计算书(需已完成验算)").pack(padx=16, pady=(16, 8), anchor="w")
    box = ctk.CTkTextbox(root, font=ctk.CTkFont(size=13))
    box.pack(fill="both", expand=True, padx=16)
    bar = ctk.CTkFrame(root, fg_color="transparent")
    bar.pack(fill="x", padx=16, pady=16)
    result = {"path": None}

    def log(msg: str) -> None:
        root.after(0, lambda: (box.insert("end", msg + "\n"), box.see("end")))

    def work() -> None:
        try:
            result["path"] = generate(None, log)
            log("\n完成。红字【待填写】处需人工补充。")
            root.after(0, lambda: open_btn.configure(state="normal"))
        except Exception as e:
            log(f"\n错误: {e}")
        root.after(0, lambda: gen_btn.configure(state="normal"))

    def start() -> None:
        box.delete("1.0", "end")
        gen_btn.configure(state="disabled")
        open_btn.configure(state="disabled")
        threading.Thread(target=work, daemon=True).start()

    gen_btn = ctk.CTkButton(bar, text="生成计算书", fg_color="#4287f5", command=start)
    gen_btn.pack(side="left")
    open_btn = ctk.CTkButton(bar, text="打开计算书", state="disabled",
                             command=lambda: os.startfile(result["path"]))
    open_btn.pack(side="left", padx=8)
    root.mainloop()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args = sys.argv[1:]
    if args and args[0] == "--ui":
        run_gui()
        return 0
    if args:
        return run_cli(args)
    run_gui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
