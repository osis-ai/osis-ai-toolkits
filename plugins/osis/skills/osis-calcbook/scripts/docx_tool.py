#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Edit Word (.docx) documents via small CLI steps: clear media, read structure,
modify text, insert paragraphs/tables/images. By default writes <name>_working.docx.

Show usage without a document:
  python docx_tool.py --help
  python docx_tool.py commands
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def resolve_output_path(
    input_docx: str, explicit: Optional[str], in_place: bool
) -> str:
    """Resolve save path: explicit -o > --in-place > default *_working.docx."""
    if explicit:
        return explicit
    if in_place:
        return input_docx
    p = Path(input_docx)
    return str(p.with_name(f"{p.stem}_working{p.suffix}"))


def load_table_json_payload(source: str) -> Dict[str, Any]:
    """Load table JSON from string, @path, or '-' (stdin). Shape: header + data rows."""
    s = source.strip()
    if s == "-":
        raw = sys.stdin.read()
        return json.loads(raw)
    if s.startswith("@"):
        path = Path(s[1:].strip())
        return json.loads(path.read_text(encoding="utf-8"))
    p = Path(s)
    if p.is_file() and s.endswith(".json"):
        return json.loads(p.read_text(encoding="utf-8"))
    return json.loads(s)


def parse_check_txt_file(filepath: str) -> Tuple[List[str], List[List[str]]]:
    """
    Parse check-result .txt: lines 1–2 are headers/titles, line 3 is column header,
    remaining lines are rows (whitespace-separated cells).
    """
    import pandas as pd

    df = pd.read_csv(
        filepath,
        sep=r"\s+",
        header=2,
        skiprows=[],
        encoding="gbk",
        on_bad_lines="skip",
    )
    headers = list(df.columns)
    data = df.values.tolist()
    return headers, data


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class ParaType(Enum):
    NORMAL = "normal"
    HEADING = "heading"
    FIGURE_CAPTION = "figure_caption"
    TABLE_CAPTION = "table_caption"
    IMAGE = "image"
    TABLE = "table"
    FORMULA = "formula"
    EMPTY = "empty"


@dataclass
class ParagraphInfo:
    index: int
    text: str
    style: str
    para_type: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Main Tool Class
# ---------------------------------------------------------------------------

class DocxTool:
    """Programmatic .docx editing (used by CLI and scripts)."""

    FIGURE_PATTERN = re.compile(r"^(图|Fig\.?|Figure)\s*\d+", re.IGNORECASE)
    TABLE_PATTERN = re.compile(r"^(表|Table)\s*\d+", re.IGNORECASE)

    NSMAP = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    }

    def __init__(self, docx_path: str):
        self.docx_path = docx_path
        self.doc = Document(docx_path)
        self.paragraphs_cache: List[ParagraphInfo] = []
        self._refresh_cache()

    # -----------------------------------------------------------------------
    # 1. Cache & Helper Methods
    # -----------------------------------------------------------------------

    def _refresh_cache(self) -> None:
        """Rebuild internal paragraph cache after document modifications."""
        self.paragraphs_cache = []
        for idx, para in enumerate(self.doc.paragraphs):
            para_type, style_name = self._detect_para_type(para)
            self.paragraphs_cache.append(
                ParagraphInfo(
                    index=idx,
                    text=para.text,
                    style=style_name,
                    para_type=para_type.value,
                )
            )

    def _detect_para_type(self, para) -> Tuple[ParaType, str]:
        """Detect paragraph type (image, caption, formula, etc.) and return (type, style_name)."""
        text = para.text.strip()
        style_name = para.style.name if para.style else "Normal"

        p = para._p
        has_drawing = bool(p.findall(".//w:drawing", namespaces=self.NSMAP))
        has_pict = bool(p.findall(".//w:pict", namespaces=self.NSMAP))
        has_blip = bool(p.findall(".//a:blip", namespaces=self.NSMAP))
        has_formula = bool(
            p.findall(".//m:oMath", namespaces=self.NSMAP)
            or p.findall(".//m:oMathPara", namespaces=self.NSMAP)
        )

        if has_formula:
            return ParaType.FORMULA, style_name

        if not text:
            return ParaType.EMPTY, style_name

        if has_drawing or has_pict or has_blip:
            if self.FIGURE_PATTERN.match(text):
                return ParaType.FIGURE_CAPTION, style_name
            return ParaType.IMAGE, style_name

        if self.FIGURE_PATTERN.match(text):
            return ParaType.FIGURE_CAPTION, style_name
        if self.TABLE_PATTERN.match(text):
            return ParaType.TABLE_CAPTION, style_name

        return ParaType.NORMAL, style_name

    @staticmethod
    def _get_save_path(output_path: Optional[str], fallback: str) -> str:
        return output_path if output_path else fallback

    def _apply_caption_style(self, para, style_name: str) -> None:
        """Attempt to set the given style on a paragraph; fallback silently."""
        try:
            style_names = [s.name for s in self.doc.styles]
            if style_name in style_names:
                para.style = style_name
            else:
                for s in self.doc.styles:
                    if style_name.lower() in s.name.lower():    # type: ignore
                        para.style = s.name
                        break
        except Exception:
            # If style application fails, keep default style
            pass

    # -----------------------------------------------------------------------
    # 2. Media Position Detection
    # -----------------------------------------------------------------------

    def _get_image_positions(self) -> List[Dict[str, Any]]:
        """Return list of dictionaries describing image paragraphs."""
        positions = []
        for idx, para in enumerate(self.doc.paragraphs):
            p = para._p
            has_drawing = bool(p.findall(".//w:drawing", namespaces=self.NSMAP))
            has_pict = bool(p.findall(".//w:pict", namespaces=self.NSMAP))
            has_blip = bool(p.findall(".//a:blip", namespaces=self.NSMAP))

            if has_drawing or has_pict or has_blip:
                positions.append(
                    {
                        "paragraph_index": idx,
                        "paragraph_style": para.style.name if para.style else "Normal",
                        "text": para.text[:50] if para.text else "(image)",
                    }
                )
        return positions

    def _get_table_positions(self) -> List[Dict[str, Any]]:
        """Return list of dictionaries describing table elements and their location relative to paragraphs."""
        positions = []
        body = self.doc._body._body
        tbl_idx = 0
        current_para_idx = 0
        W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

        for elem in body:
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == "p":
                current_para_idx += 1
            elif tag == "tbl":
                rows = len(elem.findall(f".//{W}tr"))
                cols_elem = elem.findall(f".//{W}tc")
                cols = len(cols_elem) // rows if rows > 0 else 0

                first_cell_text = ""
                for row in elem.findall(f".//{W}tr"):
                    cells = row.findall(f".//{W}tc")
                    if cells:
                        first_cell_text = "".join(
                            t.text for t in cells[0].findall(f".//{W}t") if t.text
                        )
                        break

                positions.append(
                    {
                        "table_index": tbl_idx,
                        "before_paragraph": current_para_idx - 1,
                        "rows": rows,
                        "cols": cols,
                        "first_cell": first_cell_text[:30],
                    }
                )
                tbl_idx += 1

        return positions

    def _get_effective_insert_position(self, position: int) -> int:
        """
        If the paragraph at `position` is immediately followed by one or more tables,
        return the index of the paragraph after the last such table.
        Otherwise return the original position.
        """
        if position < -1:
            position = -1
        if position == -1:
            return -1

        tables = self._get_table_positions()
        # 找出所有紧跟在 position 段落之后的表格
        following_tables = [t for t in tables if t["before_paragraph"] == position]
        if not following_tables:
            return position

        # 获取最后一个表格之后的段落索引
        # 注意：表格可能连续出现，需要找到最后一个表格
        last_table_idx = max(t["table_index"] for t in following_tables)
        # 找到紧跟在最后一个表格之后的段落（即 before_paragraph == position 且 table_index == last_table_idx 的表格后）
        # 实际需要找到文档中该表格之后的第一个段落索引
        # 简单做法：遍历段落，找到第一个索引大于 position 且不紧跟前一个表格的段落
        for para in self.paragraphs_cache:
            idx = para.index
            if idx <= position:
                continue
            # 检查该段落之前是否有表格
            tables_before_this_para = [t for t in tables if t["before_paragraph"] == idx - 1]
            if not tables_before_this_para:
                # 该段落之前没有表格，说明表格序列已结束
                return idx - 1  # 插入到这个段落之前，即表格之后
        # 如果所有剩余段落之前都有表格，说明表格一直到文档末尾，则返回 -1（文档末尾）
        return -1

    # -----------------------------------------------------------------------
    # 3. Document Modification Commands
    # -----------------------------------------------------------------------

    def clear(self, save_path: Optional[str] = None) -> Dict[str, Any]:
        """Remove all tables and image blocks; keep caption text; set sections to portrait."""
        result: Dict[str, Any] = {
            "images_removed": 0,
            "tables_removed": 0,
            "images_cleaned": 0,
            "output_path": "",
        }

        # Force all sections to portrait orientation
        for section in self.doc.sections:
            if section.page_width > section.page_height:  # type: ignore
                section.orientation = WD_ORIENT.PORTRAIT
                section.page_width, section.page_height = (
                    section.page_height,
                    section.page_width,
                )

        # Remove all tables
        table_count = len(self.doc.tables)
        for table in reversed(self.doc.tables):
            table._element.getparent().remove(table._element)
        result["tables_removed"] = table_count

        paras_to_remove = []
        paras_to_clean = []

        for para in self.doc.paragraphs:
            p = para._p
            text = para.text.strip()
            has_drawing = bool(p.findall(".//w:drawing", namespaces=self.NSMAP))
            has_pict = bool(p.findall(".//w:pict", namespaces=self.NSMAP))
            has_blip = bool(p.findall(".//a:blip", namespaces=self.NSMAP))
            has_image = has_drawing or has_pict or has_blip
            is_figure_caption = self.FIGURE_PATTERN.match(text)

            if has_image:
                if is_figure_caption:
                    paras_to_clean.append(para)
                else:
                    paras_to_remove.append(para)

        # Remove pure image paragraphs
        for para in reversed(paras_to_remove):
            para._element.getparent().remove(para._element)
        result["images_removed"] = len(paras_to_remove)

        # Clean images from figure caption paragraphs (keep text)
        for para in paras_to_clean:
            for run in para.runs[:]:
                run_elem = run._element
                has_img = (
                    run_elem.findall(".//w:drawing", namespaces=self.NSMAP)
                    or run_elem.findall(".//w:pict", namespaces=self.NSMAP)
                    or run_elem.findall(".//a:blip", namespaces=self.NSMAP)
                )
                if has_img:
                    run_elem.getparent().remove(run_elem)
        result["images_cleaned"] = len(paras_to_clean)

        out = self._get_save_path(save_path, self.docx_path)
        self.doc.save(out)
        result["output_path"] = out
        self.docx_path = out
        self._refresh_cache()

        print(
            f"Removed {result['images_removed']} images, {result['tables_removed']} tables"
        )
        print(f"Cleaned {result['images_cleaned']} figure captions")
        print(f"Saved: {out}")
        return result

    def read(
        self,
        start_index: Optional[int] = None,
        end_index: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Read paragraph listing; re-run after edits (indices change)."""
        images = self._get_image_positions()
        tables = self._get_table_positions()
        image_positions = {img["paragraph_index"]: img for img in images}

        # Group tables by the paragraph they appear after
        table_positions: Dict[int, List[Dict]] = {}
        tables_at_start: List[Dict] = []
        for tbl in tables:
            idx = tbl["before_paragraph"]
            if idx == -1:
                tables_at_start.append(tbl)
            else:
                table_positions.setdefault(idx, []).append(tbl)

        # Print tables that appear before any paragraph
        if tables_at_start:
            print("--- Tables before first paragraph ---")
            for tbl in tables_at_start:
                print(
                    f"[Table {tbl['table_index']}] {tbl['rows']}x{tbl['cols']}, "
                    f"header={repr(tbl['first_cell'][:20])}"
                )
            print()

        def one_block(idx: int, info: ParagraphInfo) -> Dict[str, Any]:
            """Build output dict for a paragraph, attaching images/tables."""
            extra_img = image_positions.get(idx)
            extra_tbls = table_positions.get(idx, [])
            d = info.to_dict()
            if extra_img:
                d["has_image"] = True
            if extra_tbls:
                d["tables_after"] = extra_tbls
            return d

        def _formula_text(idx: int) -> str:
            """Extract plain text from OMML formula."""
            p = self.doc.paragraphs[idx]._p
            return "".join(
                t.text or "" for t in p.findall(".//m:t", namespaces=self.NSMAP)
            )

        results: List[Dict[str, Any]] = []

        # Single index mode
        if start_index is not None and end_index is None:
            if not (0 <= start_index < len(self.paragraphs_cache)):
                print(
                    f"Error: index {start_index} out of range (0-{len(self.paragraphs_cache) - 1})"
                )
                return []

            info = self.paragraphs_cache[start_index]
            d = one_block(start_index, info)
            if start_index in image_positions:
                print(f"[{info.index}] [{info.style}] [IMAGE]")
            elif info.para_type == ParaType.FORMULA.value:
                ftxt = _formula_text(start_index) or "[FORMULA]"
                print(f"[{info.index}] [{info.style}] {ftxt}")
            else:
                print(f"[{info.index}] [{info.style}] {info.text}")
            for tbl in table_positions.get(start_index, []):
                print(
                    f"         └─ [TABLE {tbl['table_index']}] {tbl['rows']}x{tbl['cols']}, "
                    f"header={repr(tbl['first_cell'][:20])}"
                )
            results.append(d)
            return results

        # Range mode
        if start_index is not None and end_index is not None:
            max_idx = len(self.paragraphs_cache) - 1
            if not (0 <= start_index <= max_idx):
                print(f"Error: start index {start_index} out of range (0-{max_idx})")
                return []
            if end_index > max_idx:
                end_index = max_idx

            for idx in range(start_index, end_index + 1):
                info = self.paragraphs_cache[idx]
                has_image = idx in image_positions
                has_table = idx in table_positions

                # Skip purely empty paragraphs without media
                if (
                    info.para_type == ParaType.EMPTY.value
                    and not has_image
                    and not has_table
                ):
                    continue

                d = one_block(idx, info)
                if has_image:
                    print(f"[{info.index}] [{info.style}] [IMAGE]")
                elif info.para_type == ParaType.FORMULA.value:
                    ftxt = _formula_text(idx) or "[FORMULA]"
                    print(f"[{info.index}] [{info.style}] {ftxt}")
                else:
                    print(f"[{info.index}] [{info.style}] {info.text}")

                for tbl in table_positions.get(idx, []):
                    print(
                        f"         └─ [TABLE {tbl['table_index']}] {tbl['rows']}x{tbl['cols']}, "
                        f"header={repr(tbl['first_cell'][:20])}"
                    )
                results.append(d)

            print(
                f"\nTotal: {len(results)} paragraphs, {len(images)} images, {len(tables)} tables"
            )
            return results

        # All paragraphs mode
        for info in self.paragraphs_cache:
            idx = info.index
            has_image = idx in image_positions
            has_table = idx in table_positions
            if (
                info.para_type == ParaType.EMPTY.value
                and not has_image
                and not has_table
            ):
                continue
            d = one_block(idx, info)
            if has_image:
                print(f"[{info.index}] [{info.style}] [IMAGE]")
            elif info.para_type == ParaType.FORMULA.value:
                ftxt = _formula_text(idx) or "[FORMULA]"
                print(f"[{info.index}] [{info.style}] {ftxt}")
            else:
                print(f"[{info.index}] [{info.style}] {info.text}")
            for tbl in table_positions.get(idx, []):
                print(
                    f"         └─ [TABLE {tbl['table_index']}] {tbl['rows']}x{tbl['cols']}, "
                    f"header={repr(tbl['first_cell'][:20])}"
                )
            results.append(d)

        print(
            f"\nTotal: {len(results)} paragraphs, {len(images)} images, {len(tables)} tables"
        )
        return results

    def modify(
        self, para_index: int, new_text: str, save_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Replace paragraph text (plain text; merges runs—avoid rich formatting)."""
        if not (0 <= para_index < len(self.doc.paragraphs)):
            print(f"Error: index {para_index} out of range")
            return {
                "ok": False,
                "error": "index_out_of_range",
                "para_index": para_index,
            }

        para = self.doc.paragraphs[para_index]
        if para.runs:
            para.runs[0].text = new_text
            for run in para.runs[1:]:
                run._element.getparent().remove(run._element)
        else:
            para.add_run(new_text)

        out = self._get_save_path(save_path, self.docx_path)
        self.doc.save(out)
        self.docx_path = out
        self._refresh_cache()

        print(f"Modified paragraph [{para_index}]")
        print(f"Saved: {out}")
        return {"ok": True, "para_index": para_index, "output_path": out}

    def delete(
        self, items: List[str], save_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete paragraphs or tables by index. Use 'table:N' for table index."""
        para_indices: List[int] = []
        table_indices: List[int] = []
        failed_items: List[str] = []

        for item in items:
            item_stripped = item.strip()
            if item_stripped.lower().startswith("table:"):
                try:
                    tbl_idx = int(item_stripped.split(":", 1)[1])
                    table_indices.append(tbl_idx)
                except ValueError:
                    failed_items.append(item)
            else:
                try:
                    para_idx = int(item_stripped)
                    para_indices.append(para_idx)
                except ValueError:
                    failed_items.append(item)

        deleted_tables = 0
        for idx in sorted(set(table_indices), reverse=True):
            if 0 <= idx < len(self.doc.tables):
                table = self.doc.tables[idx]
                table._element.getparent().remove(table._element)
                deleted_tables += 1
            else:
                failed_items.append(f"table:{idx}")

        deleted_paras = 0
        for idx in sorted(set(para_indices), reverse=True):
            if 0 <= idx < len(self.doc.paragraphs):
                para = self.doc.paragraphs[idx]
                para._element.getparent().remove(para._element)
                deleted_paras += 1
            else:
                failed_items.append(str(idx))

        out = self._get_save_path(save_path, self.docx_path)
        self.doc.save(out)
        self.docx_path = out
        self._refresh_cache()

        ok_items = [i for i in items if i not in failed_items]
        print(
            f"Deleted {deleted_paras} paragraphs, {deleted_tables} tables: {ok_items}"
        )
        if failed_items:
            print(f"Failed (out of range or invalid): {failed_items}")
        print(f"Saved: {out}")
        return {
            "command": "delete",
            "deleted_paragraphs": deleted_paras,
            "deleted_tables": deleted_tables,
            "indices": ok_items,
            "failed": failed_items,
            "output_path": out,
        }

    def add(
        self,
        position: int,
        text: str,
        style: str = "Normal",
        save_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Insert a new paragraph after the specified position (-1 for end)."""
        new_para = self.doc.add_paragraph()
        new_para.text = text

        if not (position == -1 or position >= len(self.doc.paragraphs)):
            effective_pos = self._get_effective_insert_position(position)
            target_p = self.doc.paragraphs[effective_pos]._element
            target_p.addnext(new_para._element)

        self._apply_caption_style(new_para, style)

        out = self._get_save_path(save_path, self.docx_path)
        self.doc.save(out)
        self.docx_path = out
        self._refresh_cache()

        print(f"Added paragraph at [{position}] with style [{style}]")
        print(f"Saved: {out}")
        return {"ok": True, "position": position, "style": style, "output_path": out}

    # -----------------------------------------------------------------------
    # 4. Insertion Helpers (Shared by add_table, add_image, addcheck)
    # -----------------------------------------------------------------------

    def _insert_elements_with_caption(
        self,
        position: int,
        elements: List[Any],
        caption: Optional[str],
        caption_style: str,
        caption_position: str,
    ) -> None:
        """Generic insertion: place a list of XML elements after 'position', with optional caption before/after."""

        elements_to_insert: List[Any] = []

        if caption:
            caption_para = self.doc.add_paragraph()
            caption_para.text = caption
            self._apply_caption_style(caption_para, caption_style)

            if caption_position == "after":
                elements_to_insert += elements + [caption_para._element]
            else:  # "before"
                elements_to_insert += [caption_para._element] + elements
        else:
            elements_to_insert += elements

        if position == -1 or position >= len(self.doc.paragraphs):
            for elem in elements_to_insert:
                self.doc._body._body.append(elem)
            if position != -1:
                print(
                    f"Warning: position {position} out of range (paragraphs: {len(self.doc.paragraphs)}). Appended to document end."
                )
        else:
            target_p = self.doc.paragraphs[position]._element
            for elem in elements_to_insert:
                target_p.addnext(elem)
                target_p = elem

    def _move_elements_to_position(self, position: int, elements: List[Any]) -> None:
        """Remove elements from document body and reinsert after the target paragraph."""
        if position == -1 or position >= len(self.doc.paragraphs):
            # Already at end, no move needed
            return

        target_para = self.doc.paragraphs[position]
        insert_point = target_para._element

        # Detach from current location
        for elem in elements:
            elem.getparent().remove(elem)

        # Insert sequentially
        current = insert_point
        for elem in elements:
            current.addnext(elem)
            current = elem

    # -----------------------------------------------------------------------
    # 5. Table & Image Insertion Commands
    # -----------------------------------------------------------------------

    def _parse_table_json_obj(
        self, data_obj: Any
    ) -> Tuple[Optional[List[str]], List[List[Any]]]:
        """Validate and extract header/data from JSON object."""
        if not isinstance(data_obj, dict):
            raise ValueError("JSON root must be an object with 'header' and 'data'")
        header = data_obj.get("header")
        data = data_obj.get("data", [])
        if not isinstance(data, list):
            raise ValueError("'data' must be an array")
        if header is not None and not isinstance(header, list):
            raise ValueError("'header' must be an array or omitted")
        return header, data  # type: ignore[return-value]

    def _fill_table_data(
        self,
        table,
        header: Optional[List[str]],
        data: List[List[Any]],
    ) -> None:
        """Populate a Word table with header and data rows."""
        start_row = 0
        if header:
            if len(header) != len(table.columns):
                print(
                    f"Warning: header length ({len(header)}) != columns ({len(table.columns)})"
                )
            else:
                for col_idx, cell_text in enumerate(header):
                    table.cell(0, col_idx).text = str(cell_text)
                start_row = 1

        for row_idx, row_data in enumerate(data):
            if len(row_data) != len(table.columns):
                print(
                    f"Warning: row {row_idx} length ({len(row_data)}) != columns ({len(table.columns)})"
                )
                continue
            for col_idx, cell_text in enumerate(row_data):
                if start_row + row_idx < len(table.rows):
                    table.cell(start_row + row_idx, col_idx).text = str(cell_text)

    def _apply_table_style(self, table, has_header: bool) -> None:
        """Apply consistent styling: borders, 10.5pt font, 1.5 line spacing, centered text."""
        for row in table.rows:
            for cell in row.cells:
                tc = cell._tc
                tcPr = tc.get_or_add_tcPr()

                # Borders
                borders = OxmlElement('w:tcBorders')
                for border_name in ('top', 'bottom', 'left', 'right'):
                    border = OxmlElement(f'w:{border_name}')
                    border.set(qn('w:val'), 'single')
                    border.set(qn('w:sz'), '4')
                    border.set(qn('w:space'), '0')
                    border.set(qn('w:color'), '000000')
                    borders.append(border)
                tcPr.append(borders)

                # Vertical center
                vAlign = OxmlElement('w:vAlign')
                vAlign.set(qn('w:val'), 'center')
                tcPr.append(vAlign)

                # Cell paragraph formatting
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(10.5)
                    if not paragraph.runs and paragraph.text.strip():
                        text = paragraph.text
                        paragraph.clear()
                        run = paragraph.add_run(text)
                        run.font.size = Pt(10.5)
                    paragraph.paragraph_format.line_spacing = 1.5
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Header row bold
        if has_header and len(table.rows) > 0:
            for cell in table.rows[0].cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.bold = True
                    if not paragraph.runs and paragraph.text.strip():
                        text = paragraph.text
                        paragraph.clear()
                        run = paragraph.add_run(text)
                        run.bold = True

    def add_table(
        self,
        position: int,
        json_file: str,
        caption: Optional[str] = None,
        caption_style: str = "Normal",
        caption_position: str = "after",
        save_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Insert a table from a JSON file with optional caption."""
        json_path = Path(json_file)
        if not json_path.is_file():
            print(f"Error: file not found: {json_file}")
            return {"ok": False, "error": "file_not_found", "path": json_file}

        try:
            data_obj = json.loads(json_path.read_text(encoding="utf-8"))
            header, data = self._parse_table_json_obj(data_obj)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error: {e}")
            return {"ok": False, "error": "json_parse_error", "message": str(e)}

        rows = len(data) + (1 if header else 0)
        cols = len(header) if header else (len(data[0]) if data else 0)

        if rows == 0 or cols == 0:
            print("Error: no valid data in JSON")
            return {"ok": False, "error": "empty_table"}

        table = self.doc.add_table(rows=rows, cols=cols)
        self._fill_table_data(table, header, data)
        self._apply_table_style(table, header is not None)

        effective_pos = self._get_effective_insert_position(position)
        self._insert_elements_with_caption(
            effective_pos, [table._element], caption, caption_style, caption_position
        )

        out = self._get_save_path(save_path, self.docx_path)
        self.doc.save(out)
        self.docx_path = out
        self._refresh_cache()

        print(f"Added table {rows}x{cols} with JSON data")
        if caption:
            print(f"Added caption: {caption} (position: {caption_position})")
        print(f"Saved: {out}")
        return {
            "ok": True,
            "rows": rows,
            "cols": cols,
            "caption": caption,
            "output_path": out,
        }

    def add_check(
        self,
        position: int,
        txt_file: str,
        caption: Optional[str] = None,
        caption_style: str = "Normal",
        caption_position: str = "after",
        save_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Insert a table from a .txt check file, placing it in a landscape-oriented section.
        The section is isolated with section breaks to preserve portrait orientation elsewhere.
        The table starts on a new page.
        """
        from docx.enum.text import WD_BREAK

        if not Path(txt_file).is_file():
            print(f"Error: file not found: {txt_file}")
            return {"ok": False, "error": "file_not_found", "path": txt_file}

        headers, data = parse_check_txt_file(txt_file)
        rows = len(data) + (1 if headers else 0)
        cols = len(headers) if headers else (len(data[0]) if data else 0)

        if rows == 0 or cols == 0:
            print(f"Error: no valid data in {txt_file}")
            return {"ok": False, "error": "empty_data", "path": txt_file}

        base_sect = self.doc.sections[0]

        # Record existing elements to later move the newly created ones
        body = self.doc.element.body
        existing_elems = list(body)

        # --- Build new content at the end of document (page break, landscape section, table, portrait section) ---

        # 1. Insert a manual page break so the table starts on a new page
        page_break_para = self.doc.add_paragraph()
        page_break_run = page_break_para.add_run()
        page_break_run.add_break(WD_BREAK.PAGE)

        # 2. Create landscape section (continuous section break, no automatic page break)
        landscape_sect = self.doc.add_section(WD_SECTION.CONTINUOUS)
        landscape_sect.orientation = WD_ORIENT.LANDSCAPE
        landscape_sect.page_width = base_sect.page_height
        landscape_sect.page_height = base_sect.page_width
        landscape_sect.top_margin = base_sect.top_margin
        landscape_sect.bottom_margin = base_sect.bottom_margin
        landscape_sect.left_margin = base_sect.left_margin
        landscape_sect.right_margin = base_sect.right_margin
        landscape_sect.header_distance = base_sect.header_distance
        landscape_sect.footer_distance = base_sect.footer_distance

        # 3. Optional caption before table
        if caption and caption_position == "before":
            cap_para = self.doc.add_paragraph(caption)
            self._apply_caption_style(cap_para, caption_style)

        # 4. Add table
        table = self.doc.add_table(rows=rows, cols=cols)
        self._fill_table_data(table, headers, data)
        self._apply_table_style(table, bool(headers))

        # 5. Optional caption after table
        if caption and caption_position == "after":
            cap_para = self.doc.add_paragraph(caption)
            self._apply_caption_style(cap_para, caption_style)

        # 6. Restore portrait section (continuous section break)
        portrait_sect = self.doc.add_section(WD_SECTION.CONTINUOUS)
        portrait_sect.orientation = WD_ORIENT.PORTRAIT
        portrait_sect.page_width = base_sect.page_width
        portrait_sect.page_height = base_sect.page_height
        portrait_sect.top_margin = base_sect.top_margin
        portrait_sect.bottom_margin = base_sect.bottom_margin
        portrait_sect.left_margin = base_sect.left_margin
        portrait_sect.right_margin = base_sect.right_margin
        portrait_sect.header_distance = base_sect.header_distance
        portrait_sect.footer_distance = base_sect.footer_distance

        # --- Move the newly created block to the target position ---
        new_elems = [e for e in list(body) if e not in existing_elems]
        effective_pos = self._get_effective_insert_position(position)
        self._move_elements_to_position(effective_pos, new_elems)

        out_path = self._get_save_path(save_path, self.docx_path)
        self.doc.save(out_path)
        self.docx_path = out_path
        self._refresh_cache()

        print(f"Added check table {rows}x{cols} from {txt_file} with landscape section (new page)")
        if caption:
            print(f"Added caption: {caption} (position: {caption_position})")
        print(f"Saved: {out_path}")

        return {
            "ok": True,
            "rows": rows,
            "cols": cols,
            "source": txt_file,
            "caption": caption,
            "output_path": out_path,
        }

    def add_image(
        self,
        position: int,
        image_path: str,
        caption: Optional[str] = None,
        caption_style: str = "Normal",
        caption_position: str = "after",
        save_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Insert an image with optional caption, scaled to page width."""
        if not Path(image_path).is_file():
            print(f"Error: image not found: {image_path}")
            return {"ok": False, "error": "file_not_found", "path": image_path}

        img_para = self.doc.add_paragraph()
        run = img_para.add_run()
        section = self.doc.sections[0]
        content_width_inches = (
            section.page_width - section.left_margin - section.right_margin  # type: ignore
        ) / 914400.0
        run.add_picture(image_path, width=Inches(content_width_inches))

        effective_pos = self._get_effective_insert_position(position)
        self._insert_elements_with_caption(
            effective_pos, [img_para._element], caption, caption_style, caption_position
        )

        out = self._get_save_path(save_path, self.docx_path)
        self.doc.save(out)
        self.docx_path = out
        self._refresh_cache()

        print(f"Added image: {image_path}")
        if caption:
            print(f"Added caption: {caption} (position: {caption_position})")
        print(f"Saved: {out}")
        return {
            "ok": True,
            "image_path": image_path,
            "caption": caption,
            "output_path": out,
        }

    # -----------------------------------------------------------------------
    # 6. Table of Contents
    # -----------------------------------------------------------------------

    def addtoc(
        self,
        style_mappings: List[Tuple[str, int]],
        save_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delete old TOC paragraphs and insert a new TOC field."""
        result: Dict[str, Any] = {
            "deleted": 0,
            "insert_position": -1,
            "output_path": "",
        }

        # Find old TOC paragraphs (style name starts with "toc" or "目录")
        toc_indices: List[int] = []
        for idx, para in enumerate(self.doc.paragraphs):
            style_name = para.style.name if para.style else "Normal"
            lower_name = style_name.lower()  # type: ignore
            if lower_name.startswith("toc") or lower_name.startswith("目录"):
                toc_indices.append(idx)

        for idx in sorted(set(toc_indices), reverse=True):
            para = self.doc.paragraphs[idx]
            para._element.getparent().remove(para._element)
            result["deleted"] += 1

        insert_pos = toc_indices[0] - 1 if toc_indices else -1

        # Build TOC instruction, e.g. TOC \o "1-3" \t "一级标题,1,二级标题,2" \h \z \u
        parts = [r'TOC \o "1-3"']
        if style_mappings:
            t_part = ",".join(f"{style},{level}" for style, level in style_mappings)
            parts.append(rf'\t "{t_part}"')
        parts.extend([r"\h", r"\z", r"\u"])
        instr = " ".join(parts)

        # Create TOC field paragraph
        p = self.doc.add_paragraph()

        # fldChar begin
        r1 = p.add_run()
        fld_begin = OxmlElement("w:fldChar")
        fld_begin.set(qn("w:fldCharType"), "begin")
        r1._r.append(fld_begin)

        # instrText
        r2 = p.add_run()
        instr_elem = OxmlElement("w:instrText")
        instr_elem.text = instr
        r2._r.append(instr_elem)

        # fldChar separate
        r3 = p.add_run()
        fld_sep = OxmlElement("w:fldChar")
        fld_sep.set(qn("w:fldCharType"), "separate")
        r3._r.append(fld_sep)

        # placeholder
        p.add_run('（请右键此处选择"更新域"以生成目录）')

        # fldChar end
        r4 = p.add_run()
        fld_end = OxmlElement("w:fldChar")
        fld_end.set(qn("w:fldCharType"), "end")
        r4._r.append(fld_end)

        # Insert after the paragraph before the first deleted TOC entry
        if insert_pos == -1 or insert_pos >= len(self.doc.paragraphs):
            self.doc._body._body.append(p._element)
        else:
            target_p = self.doc.paragraphs[insert_pos]._element
            target_p.addnext(p._element)

        result["insert_position"] = (
            insert_pos if insert_pos != -1 else len(self.doc.paragraphs) - 1
        )

        out = self._get_save_path(save_path, self.docx_path)
        self.doc.save(out)
        result["output_path"] = out
        self.docx_path = out
        self._refresh_cache()

        print(f"Deleted {result['deleted']} old TOC entries")
        print(f"Inserted TOC field at position {result['insert_position']}")
        print(f"Saved: {out}")
        return result

    # -----------------------------------------------------------------------
    # 7. List Media Summary
    # -----------------------------------------------------------------------

    def list_media(self) -> Dict[str, Any]:
        """Print summary of paragraphs, images, and tables."""
        images = self._get_image_positions()
        tables = self._get_table_positions()

        print("Summary:")
        print(f"  paragraphs: {len(self.paragraphs_cache)}")
        print(f"  images: {len(images)}")
        print(f"  tables: {len(tables)}")

        if images:
            print(f"\n--- Images ({len(images)}) ---")
            for img in images:
                print(
                    f"  [P{img['paragraph_index']}] {img['paragraph_style']}: {img['text']}"
                )

        if tables:
            print(f"\n--- Tables ({len(tables)}) ---")
            for tbl in tables:
                print(
                    f"  [Table {tbl['table_index']}] {tbl['rows']}x{tbl['cols']}, "
                    f"after P{tbl['before_paragraph']}, header={repr(tbl['first_cell'])}"
                )

        return {"images": images, "tables": tables}


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------

CLI_EPILOG = """
output:
  Default (in-place): overwrites the input file.

commands:
  clear              Drop all tables; remove image-only blocks; strip drawings from
                     figure-caption lines (Fig/Figure/...); force portrait.
  read [i [j]]       List paragraphs, one index i, or inclusive range [i, j].
                     Re-run after edits—indices shift.
  list               Show paragraph / image / table locations.
  modify i text      Set paragraph i to plain text (merges runs).
  delete / del i [i ...]  Delete paragraph(s) or table(s); larger indices first. Use table:n for tables.
  add pos text [style]  Insert after paragraph pos; pos=-1 appends. Default style Normal.
  addtoc style1 level1 [style2 level2 ...]  Delete old TOC entries and insert a TOC field.
                     Map custom heading styles to outline levels (e.g. 一级标题 1 二级标题 2).
  addtable pos json_file caption style [before|after]  Insert table with caption and style.
                     json_file: path to JSON file with {"header":[...],"data":[[...],...]}
                     caption: table caption text (required)
                     style: caption style name (required)
                     before|after: caption position relative to table (default: before)
  addcheck pos txt_file caption style [before|after]  Table from check .txt with caption and style.
                     txt_file: path to whitespace-separated data file (first two lines skipped)
                     caption: table caption text (required)
                     style: caption style name (required)
                     before|after: caption position relative to table (default: before)
  addimage pos img caption style [before|after]  Insert image with caption and style.
                     caption: image caption text (required)
                     style: caption style name (required)
                     before|after: caption position relative to image (default: after)

examples:
  docx_tool.py template.docx clear
  docx_tool.py template.docx read
  docx_tool.py template.docx read 0 30
  docx_tool.py template.docx addtable 12 data.json "表1.1 材料表" "图表名字" after
  docx_tool.py template.docx addcheck 20 check.txt "表4.1 验算表" "图表名字" after
  docx_tool.py template.docx addimage 152 img.jpg "图2.1 计算模型图" "图表名字" after
  docx_tool.py template.docx addimage 152 img.jpg "图2.1 计算模型图" "图表名字" before
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="docx_tool.py",
        description="Small-step .docx editor. Default: overwrites input (in-place).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=CLI_EPILOG,
    )
    p.add_argument(
        "--in-place",
        action="store_true",
        default=True,
        help="overwrite the input file (default: True)",
    )
    p.add_argument("input_docx", help="input .docx file")
    p.add_argument(
        "command",
        choices=[
            "clear",
            "read",
            "list",
            "modify",
            "delete",
            "add",
            "addtoc",
            "addtable",
            "addcheck",
            "addimage",
            "help",
        ],
        nargs="?",
        default="help",
        metavar="CMD",
        help="subcommand",
    )
    p.add_argument(
        "args", nargs=argparse.REMAINDER, metavar="ARG", help="subcommand arguments"
    )
    return p


def resolve_position(arg: str) -> int:
    """Parse position argument - returns the paragraph index."""
    return int(arg)


def main() -> None:
    argv = sys.argv[1:]

    # Help-only modes: no .docx required
    if argv == ["commands"]:
        print(CLI_EPILOG.strip())
        return
    if len(argv) == 1 and argv[0] == "help":
        build_parser().print_help()
        return

    parser = build_parser()
    ns = parser.parse_args(argv)

    if ns.command == "help":
        parser.print_help()
        return

    input_path = ns.input_docx
    if not Path(input_path).is_file():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        tool = DocxTool(input_path)

        if ns.command == "clear":
            tool.clear()

        elif ns.command == "read":
            args = ns.args
            if len(args) == 0:
                tool.read()
            elif len(args) == 1:
                tool.read(start_index=int(args[0]))
            elif len(args) == 2:
                tool.read(start_index=int(args[0]), end_index=int(args[1]))
            else:
                print("Usage: read [start] [end]", file=sys.stderr)
                sys.exit(2)

        elif ns.command == "list":
            tool.list_media()

        elif ns.command == "modify":
            if len(ns.args) < 2:
                print("Usage: modify <index> <text>", file=sys.stderr)
                sys.exit(2)
            idx = int(ns.args[0])
            new_text = ns.args[1]
            tool.modify(idx, new_text, save_path=None)

        elif ns.command in ("delete", "del"):
            if not ns.args:
                print(
                    "Usage: delete <index|table:n> [<index|table:n> ...]",
                    file=sys.stderr,
                )
                sys.exit(2)
            tool.delete(ns.args, save_path=None)

        elif ns.command == "add":
            if len(ns.args) < 2:
                print(
                    "Usage: add <position> <text> [style]",
                    file=sys.stderr,
                )
                sys.exit(2)
            pos_arg = ns.args[0]
            try:
                position = resolve_position(pos_arg)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(2)
            if len(ns.args) == 2:
                text, style = ns.args[1], "Normal"
            else:
                style = ns.args[-1]
                text = " ".join(ns.args[1:-1])
            tool.add(position, text, style, save_path=None)

        elif ns.command == "addtoc":
            args = ns.args
            if len(args) < 2 or len(args) % 2 != 0:
                print(
                    "Usage: addtoc <style1> <level1> [<style2> <level2> ...]",
                    file=sys.stderr,
                )
                sys.exit(2)
            style_mappings = []
            for i in range(0, len(args), 2):
                try:
                    level = int(args[i + 1])
                except ValueError:
                    print(
                        f"Error: level must be an integer, got '{args[i + 1]}'",
                        file=sys.stderr,
                    )
                    sys.exit(2)
                style_mappings.append((args[i], level))
            tool.addtoc(style_mappings, save_path=None)

        elif ns.command == "addtable":
            args = ns.args
            if len(args) < 4:
                print(
                    "Usage: addtable <pos> <json_file> <caption> <style> [before|after]",
                    file=sys.stderr,
                )
                sys.exit(2)

            pos_arg = args[0]
            try:
                position = resolve_position(pos_arg)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(2)

            json_file = args[1]
            caption = args[2]
            caption_style = args[3]

            caption_position = "before"
            if len(args) > 4 and args[4] in ("before", "after"):
                caption_position = args[4]

            if not Path(json_file).is_file():
                print(f"Error: JSON file not found: {json_file}", file=sys.stderr)
                sys.exit(2)

            tool.add_table(
                position,
                json_file,
                caption=caption,
                caption_style=caption_style,
                caption_position=caption_position,
                save_path=None,
            )

        elif ns.command == "addcheck":
            if len(ns.args) < 4:
                print(
                    "Usage: addcheck <pos> <txt_file> <caption> <style> [before|after]",
                    file=sys.stderr,
                )
                sys.exit(2)

            pos_arg = ns.args[0]
            try:
                position = resolve_position(pos_arg)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(2)

            txt_file = ns.args[1]
            caption = ns.args[2]
            caption_style = ns.args[3]

            caption_position = "before"
            if len(ns.args) > 4 and ns.args[4] in ("before", "after"):
                caption_position = ns.args[4]

            tool.add_check(
                position,
                txt_file,
                caption=caption,
                caption_style=caption_style,
                caption_position=caption_position,
                save_path=None,
            )

        elif ns.command == "addimage":
            if len(ns.args) < 4:
                print(
                    "Usage: addimage <pos> <image_path> <caption> <style> [before|after]",
                    file=sys.stderr,
                )
                sys.exit(2)

            pos_arg = ns.args[0]
            try:
                position = resolve_position(pos_arg)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(2)

            image_path = ns.args[1]
            caption = ns.args[2]
            caption_style = ns.args[3]

            caption_position = "after"
            if len(ns.args) > 4 and ns.args[4] in ("before", "after"):
                caption_position = ns.args[4]

            tool.add_image(
                position,
                image_path,
                caption=caption,
                caption_style=caption_style,
                caption_position=caption_position,
                save_path=None,
            )

        else:
            parser.print_help()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()