"""模板:字符串大写转换(示例功能,替换为你的实际逻辑)。

本文件是 A 形态(GUI 插件)。B 形态(纯 CLI,忽略 --ui)的 main() 写法见 SKILL.md §2。

GUI:  python main.py --ui
CLI:  python main.py "hello"
"""
import argparse
import sys

import customtkinter as ctk


# ---- 核心逻辑:GUI 与 CLI 共用,只写这一份 ----
def do_work(text: str) -> str:
    return text.upper()


# ---- CLI 模式 ----
def run_cli(args: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="template", description="字符串大写转换（命令行）")
    parser.add_argument("text", help="要转换的文本")
    ns = parser.parse_args(args)
    try:
        print(do_work(ns.text))
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    return 0


# ---- GUI 模式 ----
def run_gui() -> None:
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    root.title("template 字符串大写")
    root.geometry("360x180")

    entry = ctk.CTkEntry(root, font=ctk.CTkFont(size=18), justify="center")
    entry.pack(fill="x", padx=16, pady=(16, 8))
    result = ctk.CTkLabel(root, text=" ", font=ctk.CTkFont(size=20))
    result.pack(expand=True)

    def convert() -> None:
        try:
            result.configure(text=do_work(entry.get()))
        except Exception as e:
            result.configure(text=f"错误: {e}")

    ctk.CTkButton(root, text="转换", fg_color="#4287f5", command=convert).pack(
        fill="x", padx=16, pady=(8, 16)
    )
    root.mainloop()


def main() -> int:
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
