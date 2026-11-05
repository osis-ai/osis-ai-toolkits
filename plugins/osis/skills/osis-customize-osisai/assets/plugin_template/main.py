# -*- coding: utf-8 -*-
"""模板后端:字符串大写转换(示例功能,替换为实际逻辑)。

界面(ui.tsx)用 host.python 调本文件;AI / 命令行也直接调:
    python main.py "hello"
进度逐行打到 stdout;最后一行是 JSON 结果;错误写 stderr、退出码 1。
"""
import argparse
import json
import sys


# ---- 核心逻辑 ----
def do_work(text: str) -> str:
    return text.upper()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="字符串大写转换")
    parser.add_argument("text", help="要转换的文本")
    ns = parser.parse_args()
    try:
        print(f"转换 {len(ns.text)} 个字符…", flush=True)
        out = do_work(ns.text)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    print(json.dumps({"output": out}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
