#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
renumber.py - Markdown 文档标题与图表题注重编号工具

用法:
    python renumber.py input.md output.md [选项]

功能:
    1. 按实际层级为 Markdown 标题重新编号（1. / 1.1. / 1.1.1.）
    2. 按出现顺序为图/表题注重新编号
    3. 自动更新正文中简单的图/表交叉引用
    4. 输出新旧编号映射表（供AI手动修正复杂引用）

选项:
    --heading                  启用标题重编号
    --figure-prefix "图"       图题注前缀（默认：图）
    --figure-format "{chapter}.{seq}"  图编号格式（默认：{chapter}.{seq}）
    --table-prefix "表"        表题注前缀（默认：表）
    --table-format "{chapter}.{seq}"   表编号格式（默认：{chapter}.{seq}）

格式占位符:
    {chapter}  - 当前所在一级章节的编号
    {seq}      - 图/表在该章节内的顺序号

示例:
    # 标准格式（图3.1, 表1.1-1）
    python renumber.py calc.md calc_numbered.md --heading \
        --figure-format "{chapter}.{seq}" --table-format "{chapter}.{seq}"

    # 连续编号（图1, 图2, 表1, 表2）
    python renumber.py calc.md calc_numbered.md --heading \
        --figure-format "{seq}" --table-format "{seq}"

    # 英文格式（Fig. 3.1, Table 3.1）
    python renumber.py calc.md calc_numbered.md --heading \
        --figure-prefix "Fig." --figure-format " {chapter}.{seq}" \
        --table-prefix "Table" --table-format " {chapter}.{seq}"
"""

import argparse
import re
import sys
from pathlib import Path


def renumber_markdown(
    input_path: str,
    output_path: str,
    heading: bool = False,
    figure_prefix: str = "图",
    figure_format: str = "{chapter}.{seq}",
    table_prefix: str = "表",
    table_format: str = "{chapter}.{seq}",
):
    """执行重编号"""

    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 标题计数器
    heading_counters = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}

    # 图/表计数器
    figure_seq = 0
    table_seq = 0
    current_chapter = "0"

    # 新旧编号映射（用于交叉引用更新和日志输出）
    figure_map = {}  # 旧编号文本 -> 新编号文本（不含前缀）
    table_map = {}

    new_lines = []

    # 编译正则：匹配标题（# ## ### 等）
    heading_re = re.compile(r"^(#{1,6})\s+(.*)$")

    # 编译正则：匹配图/表题注（以指定前缀开头，后面可选跟数字编号和描述）
    # 注意：不处理 Markdown 图片行 ![...](...)
    figure_re = re.compile(
        rf"^({re.escape(figure_prefix)})\s*([\d\.\-]*)\s*(.*)$"
    )
    table_re = re.compile(
        rf"^({re.escape(table_prefix)})\s*([\d\.\-]*)\s*(.*)$"
    )

    for line in lines:
        stripped = line.strip()

        # 跳过空行和 Markdown 图片行
        if not stripped or stripped.startswith("!["):
            new_lines.append(line)
            continue

        # 1. 处理标题
        heading_match = heading_re.match(stripped)
        if heading_match and heading:
            level = len(heading_match.group(1))
            text = heading_match.group(2)

            # 清除标题中已有的旧编号（如 "1.1. 工程概况" -> "工程概况"）
            text = re.sub(r"^[\d\.]+\s*", "", text)

            # 更新计数器
            heading_counters[level] += 1
            for l in range(level + 1, 7):
                heading_counters[l] = 0

            # 构建新编号
            number = ".".join(str(heading_counters[l]) for l in range(1, level + 1)) + "."
            indent = " " * (len(line) - len(line.lstrip()))
            new_lines.append(f"{indent}{ '#' * level } {number} {text}\n")

            # 更新当前章节（一级标题变化时重置图/表计数器）
            if level == 1:
                current_chapter = str(heading_counters[1])
                figure_seq = 0
                table_seq = 0

            continue

        # 2. 处理图题注
        fig_match = figure_re.match(stripped)
        if fig_match and fig_match.group(3):  # 确保有描述文字，避免误匹配普通段落
            old_num = fig_match.group(2)
            desc = fig_match.group(3)
            figure_seq += 1

            # 构建新编号
            new_number = figure_format.replace("{chapter}", current_chapter).replace(
                "{seq}", str(figure_seq)
            )
            new_lines.append(f"{figure_prefix}{new_number} {desc}\n")

            # 记录映射（用于后续交叉引用更新）
            if old_num:
                figure_map[old_num] = new_number
            continue

        # 3. 处理表题注
        tab_match = table_re.match(stripped)
        if tab_match and tab_match.group(3):
            old_num = tab_match.group(2)
            desc = tab_match.group(3)
            table_seq += 1

            new_number = table_format.replace("{chapter}", current_chapter).replace(
                "{seq}", str(table_seq)
            )
            new_lines.append(f"{table_prefix}{new_number} {desc}\n")

            if old_num:
                table_map[old_num] = new_number
            continue

        # 4. 普通行：尝试更新正文中的交叉引用
        # 策略：按旧编号长度从长到短排序，避免短编号误替换（如 "3.10" 先于 "3.1"）
        new_line = line
        for old_num in sorted(figure_map.keys(), key=len, reverse=True):
            new_num = figure_map[old_num]
            # 匹配 "图旧编号"、"见图旧编号"、"如图旧编号所示" 等上下文
            pattern = rf"({re.escape(figure_prefix)})(\s*)({re.escape(old_num)})([^\d\.]|$)"
            replacement = rf"\g<1>\g<2>{new_num}\g<4>"
            new_line = re.sub(pattern, replacement, new_line)

        for old_num in sorted(table_map.keys(), key=len, reverse=True):
            new_num = table_map[old_num]
            pattern = rf"({re.escape(table_prefix)})(\s*)({re.escape(old_num)})([^\d\.]|$)"
            replacement = rf"\g<1>\g<2>{new_num}\g<4>"
            new_line = re.sub(pattern, replacement, new_line)

        new_lines.append(new_line)

    # 写入输出文件
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    # 输出映射表
    print(f"重编号完成: {output_path}")

    if heading:
        print("\n标题已重新编号")

    if figure_map:
        print("\n图编号映射（旧 -> 新）:")
        for old, new in sorted(figure_map.items()):
            print(f"  {figure_prefix}{old} -> {figure_prefix}{new}")

    if table_map:
        print("\n表编号映射（旧 -> 新）:")
        for old, new in sorted(table_map.items()):
            print(f"  {table_prefix}{old} -> {table_prefix}{new}")

    if figure_map or table_map:
        print(
            "\n提示: 正文中简单的交叉引用已自动更新。"
            "如有复杂引用未更新，请根据上述映射表手动修正。"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Markdown 文档标题与图表题注重编号工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 标准中文格式（图3.1, 表1.1）
  python renumber.py calc.md calc_numbered.md --heading

  # 连续编号（图1, 图2, 表1, 表2）
  python renumber.py calc.md calc_numbered.md --heading \\
      --figure-format "{seq}" --table-format "{seq}"

  # 英文格式（Fig. 3.1, Table 3.1）
  python renumber.py calc.md calc_numbered.md --heading \\
      --figure-prefix "Fig." --figure-format " {chapter}.{seq}" \\
      --table-prefix "Table" --table-format " {chapter}.{seq}"
        """,
    )
    parser.add_argument("input", help="输入的 .md 文件路径")
    parser.add_argument("output", help="输出的 .md 文件路径")
    parser.add_argument(
        "--heading", action="store_true", help="启用标题重编号（按 # ## ### 的实际层级）"
    )
    parser.add_argument(
        "--figure-prefix", default="图", help='图题注前缀（默认："图"）'
    )
    parser.add_argument(
        "--figure-format",
        default="{chapter}.{seq}",
        help='图编号格式（默认："{chapter}.{seq}"，可用占位符：{chapter}, {seq}）',
    )
    parser.add_argument(
        "--table-prefix", default="表", help='表题注前缀（默认："表"）'
    )
    parser.add_argument(
        "--table-format",
        default="{chapter}.{seq}",
        help='表编号格式（默认："{chapter}.{seq}"，可用占位符：{chapter}, {seq}）',
    )

    args = parser.parse_args()

    if not Path(args.input).is_file():
        print(f"错误：文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)

    renumber_markdown(
        args.input,
        args.output,
        heading=args.heading,
        figure_prefix=args.figure_prefix,
        figure_format=args.figure_format,
        table_prefix=args.table_prefix,
        table_format=args.table_format,
    )


if __name__ == "__main__":
    main()
