#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docx_to_md.py - 将计算书模板 DOCX 转换为 Markdown 格式

用法:
    python docx_to_md.py <input.docx> [output.md] [--h1 style1] [--h2 style2] ... [--auto-number]

    如果不指定 output.md，默认输出到 <input>_template.md

功能:
    1. 提取段落文本（根据 --h1~--h6 参数识别标题）
    2. 提取表格结构（转换为 markdown 表格，空表用占位符）
    3. 识别图片位置（用占位符标记，区分题注前后）
    4. 识别题注（图/表编号）
    5. 提取公式（尽可能转换为 LaTeX 格式）
    6. 自动编号（--auto-number 参数）
    7. 输出干净的 markdown，方便后续填充数据

标题样式指定:
    通过 --h1 ~ --h6 参数指定 Word 样式名对应的 Markdown 标题级别

    示例:
        python docx_to_md.py input.docx --h1 "一级标题" --h2 "二级标题" --h3 "三级标题"
        python docx_to_md.py input.docx --h1 "Heading 1" --h2 "Heading 2" --h3 "Heading 3"

    注意：建议从 --h1 开始对应文档的一级标题，不要包含"主标题"等文档标题

自动编号:
    添加 --auto-number 参数会自动为标题添加编号
    例如：
        # 1. 项目基本信息
        ## 1.1 工程概况
        ### 1.1.1 详细说明

查看文档样式:
    python docx_to_md.py input.docx --list-styles

输出格式:
    普通段落: 直接输出文本
    标题: # 标题文本 或 ## 标题文本 等
    图片+题注:
        ![图片占位符](图片路径)
        图X.X 题注文字
        或
        图X.X 题注文字
        ![图片占位符](图片路径)
    表格+题注:
        表X.X 题注文字
        | {{表格数据}} |
    公式: $latex公式$ 或 纯文本
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

try:
    from docx import Document
except ImportError:
    print("错误：需要安装 python-docx。运行: pip install python-docx")
    sys.exit(1)


class DocxToMdConverter:
    """DOCX 转 Markdown 转换器"""

    # 匹配题注的正则
    FIGURE_PATTERN = re.compile(r"^(图|Fig\.?|Figure)\s*[\d\.]+\s*")
    TABLE_PATTERN = re.compile(r"^(表|Table)\s*[\d\.]+\s*")

    # 需要填充数据的占位文本
    PLACEHOLDER_TEXTS = [
        "请自行补充相关内容！",
        "（仅供参考！）",
        "请自行补充基频！",
    ]

    def __init__(
        self,
        docx_path: str,
        heading_styles: Optional[Dict[int, str]] = None,
        auto_number: bool = False,
    ):
        """
        Args:
            docx_path: DOCX 文件路径
            heading_styles: 标题样式映射，如 {1: "一级标题", 2: "二级标题"}
            auto_number: 是否自动添加标题编号
        """
        self.docx_path = Path(docx_path)
        self.doc = Document(docx_path)
        self.md_lines: List[str] = []
        self._table_counter = 0
        self._figure_counter = 0
        self._in_toc = False
        self.auto_number = auto_number

        # 标题编号计数器
        self.heading_counters: Dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}

        # 处理标题样式映射
        self.heading_styles: Dict[str, int] = {}
        if heading_styles:
            for level, style_name in heading_styles.items():
                if style_name and 1 <= level <= 6:
                    self.heading_styles[style_name.lower()] = level

    def _get_style_name(self, elem) -> Optional[str]:
        """获取段落的样式名"""
        pStyle = elem.find(
            ".//w:pStyle",
            namespaces={
                "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            },
        )
        if pStyle is not None:
            style_id = pStyle.get(
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val"
            )
            if style_id:
                for style in self.doc.styles:
                    if style.style_id == style_id:
                        return style.name
        return None

    def _get_heading_level(self, style_name: Optional[str]) -> int:
        """根据样式名获取标题级别，未配置则返回0"""
        if not style_name:
            return 0

        style_lower = style_name.lower()

        # 精确匹配
        if style_lower in self.heading_styles:
            return self.heading_styles[style_lower]

        # 模糊匹配（包含关系）
        for mapped_style, level in self.heading_styles.items():
            if mapped_style in style_lower or style_lower in mapped_style:
                return level

        return 0

    def _update_heading_number(self, level: int) -> str:
        """更新标题编号并返回编号字符串"""
        if not self.auto_number:
            return ""

        # 增加当前级别计数器
        self.heading_counters[level] += 1

        # 重置更低级别的计数器
        for l in range(level + 1, 7):
            self.heading_counters[l] = 0

        # 构建编号字符串
        numbers = []
        for l in range(1, level + 1):
            numbers.append(str(self.heading_counters[l]))

        return ".".join(numbers) + ". "

    def convert(self) -> str:
        """执行转换，返回 markdown 字符串"""
        self.md_lines = []
        self._table_counter = 0
        self._figure_counter = 0
        self._in_toc = False
        self.heading_counters = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}

        # 遍历文档中的所有元素（段落和表格交替出现）
        body = self.doc.element.body
        nsmap_w = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        nsmap_m = {"m": "http://schemas.openxmlformats.org/officeDocument/2006/math"}

        for elem in body:
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            if tag == "p":
                self._process_paragraph_element(elem, nsmap_w, nsmap_m)
            elif tag == "tbl":
                self._process_table_element(elem, nsmap_w)

        return "".join(self.md_lines)

    def _process_paragraph_element(self, elem, nsmap_w, nsmap_m) -> None:
        """处理段落元素"""
        # 提取普通文本（用于快速检查）
        texts = []
        for t in elem.findall(".//w:t", namespaces=nsmap_w):
            if t.text:
                texts.append(t.text)

        text = "".join(texts).strip()

        # 跳过警告信息
        if text and "Evaluation Warning" in text:
            return

        # 检测目录区域
        if text == "目录":
            self._in_toc = True
            self.md_lines.append(f"\n{text}\n\n")
            return

        # 检测目录结束（遇到非目录内容）
        if self._in_toc and text:
            if not re.match(r"^\d+\.\s*.*\d+$", text):
                self._in_toc = False
            else:
                return

        # 获取样式名和标题级别
        style_name = self._get_style_name(elem)
        heading_level = self._get_heading_level(style_name)

        # 检测是否有图片（包括 w:r/w:pict 和 w:r/w:drawing）
        has_image = bool(
            elem.findall(".//w:drawing", namespaces=nsmap_w)
            or elem.findall(".//w:pict", namespaces=nsmap_w)
        )

        # 检测是否有公式（OMML 或 EQ 域）
        has_formula = bool(
            elem.findall(".//m:oMath", namespaces=nsmap_m)
            or elem.findall(".//m:oMathPara", namespaces=nsmap_m)
        )
        has_eq_field = bool(
            elem.findall(".//w:instrText", namespaces=nsmap_w)
        )

        # 处理包含公式、图片或 EQ 域的段落（混合内容）
        if has_formula or has_image or has_eq_field:
            self._process_mixed_paragraph(elem, nsmap_w, nsmap_m, heading_level)
            return

        # 处理普通文本段落
        if not text:
            return

        if heading_level > 0:
            # 标题
            number = self._update_heading_number(heading_level)
            self.md_lines.append(f"\n{'#' * heading_level} {number}{text}\n\n")
        elif self.FIGURE_PATTERN.match(text):
            # 图题注 - 清除原有编号，保留"图/Fig + 描述文字"
            clean_text = self.FIGURE_PATTERN.sub(r"\1 ", text).strip()
            self.md_lines.append(f"\n{clean_text}\n\n")
        elif self.TABLE_PATTERN.match(text):
            # 表题注 - 清除原有编号，保留"表/Table + 描述文字"
            clean_text = self.TABLE_PATTERN.sub(r"\1 ", text).strip()
            self.md_lines.append(f"\n{clean_text}\n\n")
        elif text in self.PLACEHOLDER_TEXTS:
            # 占位文本
            placeholder = self._get_placeholder_name(text)
            self.md_lines.append(f"\n{{{{{placeholder}}}}}\n\n")
        else:
            # 普通段落
            self.md_lines.append(f"{text}\n\n")

    def _process_mixed_paragraph(self, elem, nsmap_w, nsmap_m, heading_level) -> None:
        """处理包含公式、图片、EQ域或混合内容的段落"""
        content_parts = []
        has_image_in_para = False

        # 遍历段落的所有子元素
        for child in elem:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

            if tag == "r":
                # Run 元素，可能包含文本、公式、EQ域或图片
                # 先检查是否包含图片
                has_drawing = bool(child.findall("w:drawing", namespaces=nsmap_w))
                has_pict = bool(child.findall("w:pict", namespaces=nsmap_w))

                if has_drawing or has_pict:
                    # 图片
                    self._figure_counter += 1
                    content_parts.append(f"![图片占位符](图片路径)")
                    has_image_in_para = True
                    continue

                # 检查是否包含OMML公式
                omath = child.find("m:oMath", namespaces=nsmap_m)
                if omath is not None:
                    # OMML公式
                    latex = self._convert_omath_to_latex(omath, nsmap_m)
                    if latex:
                        content_parts.append(f"${latex}$")
                    else:
                        formula_text = self._extract_formula_from_omath(omath, nsmap_m)
                        content_parts.append("{{" + formula_text + "}}")
                    continue

                # 遍历Run内部子元素，处理普通文本和EQ域
                run_parts = []
                for sub in child:
                    sub_tag = sub.tag.split("}")[-1] if "}" in sub.tag else sub.tag
                    if sub_tag == "t":
                        if sub.text:
                            run_parts.append(sub.text)
                    elif sub_tag == "instrText":
                        if sub.text and sub.text.strip().startswith("EQ "):
                            eq_latex = self._convert_eq_to_latex(sub.text.strip())
                            if eq_latex:
                                run_parts.append(f"${eq_latex}$")
                            else:
                                run_parts.append(sub.text.strip())
                if run_parts:
                    content_parts.append("".join(run_parts))

            elif tag == "oMath":
                # 独立的公式元素
                latex = self._convert_omath_to_latex(child, nsmap_m)
                if latex:
                    content_parts.append(f"${latex}$")
                else:
                    formula_text = self._extract_formula_from_omath(child, nsmap_m)
                    content_parts.append("{{" + formula_text + "}}")

            elif tag == "oMathPara":
                # 公式段落
                for omath in child.findall("m:oMath", namespaces=nsmap_m):
                    latex = self._convert_omath_to_latex(omath, nsmap_m)
                    if latex:
                        content_parts.append(f"${latex}$")
                    else:
                        formula_text = self._extract_formula_from_omath(omath, nsmap_m)
                        content_parts.append("{{" + formula_text + "}}")

        # 合并内容
        if content_parts:
            full_text = "".join(content_parts).strip()
            if full_text:
                # 检查是否是题注
                if self.FIGURE_PATTERN.match(full_text):
                    clean_text = self.FIGURE_PATTERN.sub(r"\1 ", full_text).strip()
                    self.md_lines.append(f"\n{clean_text}\n\n")
                elif heading_level > 0:
                    number = self._update_heading_number(heading_level)
                    self.md_lines.append(
                        f"\n{'#' * heading_level} {number}{full_text}\n\n"
                    )
                else:
                    self.md_lines.append(f"\n{full_text}\n\n")

    def _convert_omath_to_latex(self, omath_elem, nsmap_m) -> Optional[str]:
        """将单个 oMath 元素转换为 LaTeX"""
        try:
            return self._omml_to_latex_recursive(omath_elem, nsmap_m)
        except Exception:
            return None

    def _extract_formula_from_omath(self, omath_elem, nsmap_m) -> str:
        """从 oMath 元素提取文本"""
        texts = []
        for t in omath_elem.findall(".//m:t", namespaces=nsmap_m):
            if t.text:
                texts.append(t.text)
        return "".join(texts)

    def _omml_to_latex_recursive(self, elem, nsmap_m) -> Optional[str]:
        """递归转换 OMML 到 LaTeX"""
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

        if tag == "t":
            return elem.text or ""

        elif tag == "r":
            texts = []
            for child in elem:
                child_latex = self._omml_to_latex_recursive(child, nsmap_m)
                if child_latex:
                    texts.append(child_latex)
            return "".join(texts)

        elif tag == "f":
            num = elem.find("m:num", namespaces=nsmap_m)
            den = elem.find("m:den", namespaces=nsmap_m)
            if num is not None and den is not None:
                num_latex = self._omml_to_latex_recursive(num, nsmap_m)
                den_latex = self._omml_to_latex_recursive(den, nsmap_m)
                if num_latex and den_latex:
                    return f"\\frac{{{num_latex}}}{{{den_latex}}}"

        elif tag == "sSub":
            base = elem.find("m:e", namespaces=nsmap_m)
            sub = elem.find("m:sub", namespaces=nsmap_m)
            if base is not None and sub is not None:
                base_latex = self._omml_to_latex_recursive(base, nsmap_m)
                sub_latex = self._omml_to_latex_recursive(sub, nsmap_m)
                if base_latex and sub_latex:
                    return f"{{{base_latex}}}_{{{sub_latex}}}"

        elif tag == "sSup":
            base = elem.find("m:e", namespaces=nsmap_m)
            sup = elem.find("m:sup", namespaces=nsmap_m)
            if base is not None and sup is not None:
                base_latex = self._omml_to_latex_recursive(base, nsmap_m)
                sup_latex = self._omml_to_latex_recursive(sup, nsmap_m)
                if base_latex and sup_latex:
                    return f"{{{base_latex}}}^{{{sup_latex}}}"

        elif tag == "sSubSup":
            base = elem.find("m:e", namespaces=nsmap_m)
            sub = elem.find("m:sub", namespaces=nsmap_m)
            sup = elem.find("m:sup", namespaces=nsmap_m)
            if base is not None:
                base_latex = self._omml_to_latex_recursive(base, nsmap_m)
                sub_latex = (
                    self._omml_to_latex_recursive(sub, nsmap_m)
                    if sub is not None
                    else ""
                )
                sup_latex = (
                    self._omml_to_latex_recursive(sup, nsmap_m)
                    if sup is not None
                    else ""
                )
                if base_latex:
                    return f"{{{base_latex}}}_{{{sub_latex}}}^{{{sup_latex}}}"

        elif tag == "rad":
            deg = elem.find("m:deg", namespaces=nsmap_m)
            base = elem.find("m:e", namespaces=nsmap_m)
            if base is not None:
                base_latex = self._omml_to_latex_recursive(base, nsmap_m)
                if deg is not None:
                    deg_latex = self._omml_to_latex_recursive(deg, nsmap_m)
                    if base_latex:
                        return f"\\sqrt[{deg_latex}]{{{base_latex}}}"
                else:
                    if base_latex:
                        return f"\\sqrt{{{base_latex}}}"

        elif tag == "d":
            beg = elem.find("m:begChr", namespaces=nsmap_m)
            end = elem.find("m:endChr", namespaces=nsmap_m)
            base = elem.find("m:e", namespaces=nsmap_m)
            if base is not None:
                base_latex = self._omml_to_latex_recursive(base, nsmap_m)
                beg_char = (
                    beg.get(
                        "{http://schemas.openxmlformats.org/officeDocument/2006/math}val",
                        "(",
                    )
                    if beg is not None
                    else "("
                )
                end_char = (
                    end.get(
                        "{http://schemas.openxmlformats.org/officeDocument/2006/math}val",
                        ")",
                    )
                    if end is not None
                    else ")"
                )
                if base_latex:
                    return f"{beg_char}{base_latex}{end_char}"

        elif tag == "nary":
            sub = elem.find("m:subArg", namespaces=nsmap_m)
            sup = elem.find("m:supArg", namespaces=nsmap_m)
            base = elem.find("m:e", namespaces=nsmap_m)
            if base is not None:
                base_latex = self._omml_to_latex_recursive(base, nsmap_m)
                sub_latex = (
                    self._omml_to_latex_recursive(sub, nsmap_m)
                    if sub is not None
                    else ""
                )
                sup_latex = (
                    self._omml_to_latex_recursive(sup, nsmap_m)
                    if sup is not None
                    else ""
                )
                if base_latex:
                    return f"\\int_{{{sub_latex}}}^{{{sup_latex}}} {base_latex}"

        # 递归处理子元素
        texts = []
        for child in elem:
            child_latex = self._omml_to_latex_recursive(child, nsmap_m)
            if child_latex:
                texts.append(child_latex)

        result = "".join(texts)
        return result if result else None

    def _convert_eq_to_latex(self, eq_text: str) -> Optional[str]:
        r"""将 Word EQ 域公式转换为 LaTeX

        EQ 域是 Word 旧版公式格式，常见语法：
        - \\s\\doN(x)  -> 下标 _{x}
        - \\s\\upN(x)  -> 上标 ^{x}
        - \\f(a,b)    -> 分数 \\frac{a}{b}
        - \\r(n,x)    -> n 次根号 \\sqrt[n]{x}

        示例:
          EQ γ\\s\\do4(0)S≤R          -> $\\gamma_{0}S \\le R$
          EQ σ\\s\\do4(st)-0.85σ\\s\\do4(pc)≤0 -> $\\sigma_{st}-0.85\\sigma_{pc} \\le 0$
        """
        if not eq_text.startswith("EQ "):
            return None

        # 去掉前缀
        content = eq_text[3:].strip()

        # 将 EQ 域语法转换为 LaTeX
        import re as _re

        # 下标: \s\doN(content) -> _{content}
        # 注意：\s 后面可能直接跟 \do 或 \up
        content = _re.sub(
            r"\\s\\do\d+\(([^)]+)\)",
            r"_{\1}",
            content,
        )
        # 上标: \s\upN(content) -> ^{content}
        content = _re.sub(
            r"\\s\\up\d+\(([^)]+)\)",
            r"^{\1}",
            content,
        )
        # 分数: \f(num,den) -> \frac{num}{den}
        content = _re.sub(
            r"\\f\(([^,]+),([^)]+)\)",
            r"\\frac{\1}{\2}",
            content,
        )
        # 根号: \r(n,value) -> \sqrt[n]{value}
        content = _re.sub(
            r"\\r\((\d+),([^)]+)\)",
            r"\\sqrt[\1]{\2}",
            content,
        )

        # 将常见的 Unicode 数学符号转换为 LaTeX 命令（可选，保持可读性）
        symbol_map = {
            "≤": "\\le ",
            "≥": "\\ge ",
            "≠": "\\ne ",
            "≈": "\\approx ",
            "∞": "\\infty ",
            "±": "\\pm ",
            "×": "\\times ",
            "÷": "\\div ",
        }
        for sym, latex_cmd in symbol_map.items():
            content = content.replace(sym, latex_cmd)

        return content.strip()

    def _get_placeholder_name(self, text: str) -> str:
        """根据占位文本返回模板变量名"""
        if "工程概况" in text or "补充相关" in text:
            return "工程概况描述"
        elif "技术标准" in text:
            return "技术标准描述"
        elif "结构概述" in text:
            return "结构概述描述"
        elif "仅供参考" in text:
            return "备注信息"
        elif "基频" in text:
            return "基频计算说明"
        elif "荷载组合" in text:
            return "荷载组合说明"
        else:
            return "待补充内容"

    def _process_table_element(self, elem, nsmap_w) -> None:
        """处理表格元素，转换为 markdown 表格"""
        W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

        rows_data = []
        for row in elem.findall(f".{W}tr"):
            row_data = []
            for cell in row.findall(f".{W}tc"):
                cell_texts = []
                for t in cell.findall(f".{W}t"):
                    if t.text:
                        cell_texts.append(t.text)
                cell_text = "".join(cell_texts).strip()
                row_data.append(cell_text)
            rows_data.append(row_data)

        if not rows_data:
            return

        # 检查表格是否为空（所有单元格都为空）
        is_empty_table = all(all(not cell for cell in row) for row in rows_data)

        if is_empty_table:
            # 空表格，只输出占位符
            self.md_lines.append("\n| {{表格数据}} |\n\n")
            return

        # 转换为 markdown 表格
        self.md_lines.append("\n")

        # 计算列数
        max_cols = max(len(row) for row in rows_data)

        # 打印表头（第一行）
        if rows_data:
            header = rows_data[0]
            header = header + [""] * (max_cols - len(header))
            self.md_lines.append("| " + " | ".join(header) + " |\n")
            self.md_lines.append("| " + " | ".join(["---"] * max_cols) + " |\n")

            # 检查数据行是否都为空
            has_data = False
            for row in rows_data[1:]:
                if any(cell for cell in row):
                    has_data = True
                    break

            if has_data:
                # 有数据，正常输出
                for row in rows_data[1:]:
                    row = row + [""] * (max_cols - len(row))
                    self.md_lines.append("| " + " | ".join(row) + " |\n")
            else:
                # 所有数据行都为空，输出占位符
                self.md_lines.append(
                    "| {{表格数据}} |" + " |".join([""] * (max_cols - 1)) + " |\n"
                )

        self.md_lines.append("\n")

    def save(self, output_path: Optional[str] = None) -> str:
        """执行转换并保存到文件"""
        md_content = self.convert()

        if output_path is None:
            output_path = str(self.docx_path.with_suffix("_template.md"))

        Path(output_path).write_text(md_content, encoding="utf-8")
        return output_path


def main():
    parser = argparse.ArgumentParser(
        description="将 DOCX 计算书模板转换为 Markdown 格式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法（不识别标题，所有文本作为普通段落）
  python docx_to_md.py 计算书案例.docx
  
  # 指定标题样式（推荐）
  python docx_to_md.py 计算书案例.docx --h1 "一级标题" --h2 "二级标题" --h3 "三级标题"
  
  # 指定标题样式并自动编号
  python docx_to_md.py 计算书案例.docx --h1 "一级标题" --h2 "二级标题" --auto-number
  
  # 英文样式
  python docx_to_md.py input.docx --h1 "Heading 1" --h2 "Heading 2" --h3 "Heading 3"
  
  # 查看文档中所有样式名
  python docx_to_md.py input.docx --list-styles

说明:
  --h1 ~ --h6 参数用于指定 Word 样式名对应的 Markdown 标题级别
  例如 --h2 "二级标题" 表示 Word 中样式名为"二级标题"的段落会转换为 ## 标题
  
  --auto-number 参数会自动为标题添加编号（如 1. 1.1 1.1.1）
  
  建议从 --h1 开始对应文档的一级标题，不要包含"主标题"等文档标题
        """,
    )
    parser.add_argument("input", help="输入的 .docx 文件路径")
    parser.add_argument("output", nargs="?", help="输出的 .md 文件路径（可选）")
    parser.add_argument("--h1", help="指定1级标题的Word样式名")
    parser.add_argument("--h2", help="指定2级标题的Word样式名")
    parser.add_argument("--h3", help="指定3级标题的Word样式名")
    parser.add_argument("--h4", help="指定4级标题的Word样式名")
    parser.add_argument("--h5", help="指定5级标题的Word样式名")
    parser.add_argument("--h6", help="指定6级标题的Word样式名")
    parser.add_argument(
        "--auto-number",
        action="store_true",
        help="自动为标题添加编号（如 1. 1.1 1.1.1）",
    )
    parser.add_argument(
        "--list-styles", action="store_true", help="列出文档中所有段落样式名，然后退出"
    )

    args = parser.parse_args()

    if not Path(args.input).is_file():
        print(f"错误：文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)

    try:
        doc = Document(args.input)

        # 列出样式模式
        if args.list_styles:
            print(f"\n文档 '{args.input}' 中的段落样式：")
            print("-" * 50)
            styles_found = set()
            for para in doc.paragraphs:
                if para.style and para.style.name:
                    styles_found.add(para.style.name)

            for style_name in sorted(styles_found):
                print(f"  - {style_name}")
            print("-" * 50)
            print("\n使用 --h1 ~ --h6 参数指定标题样式：")
            print(
                '  python docx_to_md.py input.docx --h1 "一级标题" --h2 "二级标题" --h3 "三级标题"'
            )
            return

        # 收集标题样式映射
        heading_styles = {}
        for level in range(1, 7):
            style_name = getattr(args, f"h{level}")
            if style_name:
                heading_styles[level] = style_name

        if heading_styles:
            print("使用标题样式映射：")
            for level in sorted(heading_styles.keys()):
                print(f"  H{level}: {heading_styles[level]}")
            print()

        if args.auto_number:
            print("启用自动编号\n")

        # 执行转换
        converter = DocxToMdConverter(args.input, heading_styles, args.auto_number)
        output_path = converter.save(args.output)
        print(f"转换完成: {output_path}")
        print("\n提示: 请打开 markdown 文件，将以下内容替换为实际数据：")
        print("  - {{变量名}}     -> 实际文本内容")
        print("  - {{表格数据}}   -> 实际表格数据（markdown 表格格式）")
        print("  - {{公式: xxx}}  -> LaTeX 公式或图片")
        print("  - ![图片占位符]  -> 实际图片路径")

    except Exception as e:
        print(f"转换失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
