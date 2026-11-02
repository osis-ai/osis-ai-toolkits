# -*- coding: utf-8 -*-
"""在用户的 DOCX 计算书模板上原位填写本项目数据。

  python docx_fill.py extract 模板.docx -o 模板文本.md
  python docx_fill.py apply 模板.docx 填写清单.json -o 计算书.docx

extract:列出模板全部文字(正文、表格、文本框、页眉页脚),每段、每表、每图带编号。
apply:  按清单只改指定的字,其余原样保留(样式、编号、页眉页脚、公式、域都不动)。
        清单里的【待填写：xxx】标红,提示人工补。任何一条出错都不写输出,列出全部错误。
        每次都从模板重做,改清单后直接重跑。

清单是 JSON 列表,每项一种操作:
  {"id": "P12", "find": "50 m", "replace": "45 m"}          段内替换(find 须唯一,多处加 "all": true)
  {"id": "P12", "find": "50 m", "replace": "【待填写：主跨跨径】"}
  {"id": "P20", "text": "整段新文字"}                         整段重写(段内有域/图/公式时不允许)
  {"table": "T3", "from_row": 1, "rows": [["1", "C55"]]}     表格数据行:从 from_row 起换成 rows
  {"table": "T3", "from_row": 1, "json": "json/material.json", "columns": ["材料名称", "弹性模量"]}
                                                              行数据取自 data.py 的 json(columns 可省)
                                                              "to_row": n 时第 n 行起的原行(如合计行)保留
  {"image": "I2", "path": "image/IMG_Structure.jpg"}         换图,保持显示宽度、按新图比例调高度
                                                              Word 图表(包络图常用)也编 I 号,换图时整个换成图片
  {"id": "P30", "keep": true}  /  {"table": "T5", "keep": true}  已看过、原样保留(不进遗留清单)

值里可以写 {{字段路径|格式}},从 data.py 生成的 项目数据结构.json 取数,清单因此可在别的项目上复用:
  {"id": "P100", "find": "15", "replace": "{{基本信息.节点数量}}"}
  {"id": "P595", "find": "-317.2", "replace": "{{验算表格.正截面抗弯承载能力验算.最小弯矩|.1f}}"}
  {"id": "P595", "find": "不满足", "replace": "{{验算表格.正截面抗弯承载能力验算.满足规范|满足:不满足}}"}
  {"table": "T1", "from_row": 1, "json": "{{材料参数}}"}
  {"table": "T2", "from_row": 1, "json": "{{材料参数}}", "filter": {"材料名称": "^C[0-9]"}, "columns": ["材料名称", null, "弹性模量"]}
                                     filter 按列值正则筛行;columns 里 null 表示该列留空(OSIS 无此数据)
                                     "scale": {"弹性模量": 1e-6} 按列乘系数换单位
  {"image": "I1", "path": "{{图片文件.计算模型图}}"}
字段为 null 或不存在时填【待填写：字段路径】(表格换成一行占位,图片换成占位文字);顶层字段名写错直接报错。
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "v": "urn:schemas-microsoft-com:vml",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
}


def q(tag: str) -> str:
    prefix, local = tag.split(":")
    return f"{{{NS[prefix]}}}{local}"


W_P, W_R, W_T, W_TBL, W_TR, W_TC = q("w:p"), q("w:r"), q("w:t"), q("w:tbl"), q("w:tr"), q("w:tc")
W_RPR, W_PPR, W_TCPR = q("w:rPr"), q("w:pPr"), q("w:tcPr")
MC_FALLBACK = q("mc:Fallback")
TEXT_CHILDREN = {q("w:t"), q("w:tab"), q("w:br"), q("w:cr"), q("w:sym"), q("w:noBreakHyphen"), q("w:softHyphen")}
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
DOC = "word/document.xml"
PLACEHOLDER_RE = re.compile(r"【待填写：[^】]*】")
# rPr 子元素里排在 w:color 之后的(按 schema 顺序插入 color,Word 对顺序敏感)
AFTER_COLOR = [q(f"w:{t}") for t in (
    "spacing", "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd",
    "fitText", "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath", "rPrChange")]
# settings 里排在 w:updateFields 之后的
AFTER_UPDATE_FIELDS = [q(f"w:{t}") for t in (
    "hdrShapeDefaults", "footnotePr", "endnotePr", "compat", "docVars", "rsids")] + [
    q("m:mathPr")] + [q(f"w:{t}") for t in (
    "attachedSchema", "themeFontLang", "clrSchemeMapping", "doNotIncludeSubdocsInStats",
    "doNotAutoCompressPictures", "forceUpgrade", "captions", "readModeInkLockDown", "smartTagType",
    "schemaLibrary", "shapeDefaults", "doNotEmbedSmartTags", "decimalSymbol", "listSeparator")]
EMU_PER_CM = 360000
IMAGE_TAGS = (q("a:blip"), q("v:imagedata"), q("c:chart"))  # c:chart = Word 图表,换图时整个换成图片


class PlanError(Exception):
    pass


# ---------------------------------------------------------------- 读写 docx

class Docx:
    def __init__(self, path: str):
        with zipfile.ZipFile(path) as z:
            self.infos = z.infolist()
            self.data = {i.filename: z.read(i.filename) for i in self.infos}
        self.xml: dict[str, etree._Element] = {}

    def root(self, name: str) -> etree._Element:
        if name not in self.xml:
            self.xml[name] = etree.fromstring(self.data[name])
        return self.xml[name]

    def text_parts(self) -> list[str]:
        """正文 + 页眉页脚(按文件名排序,编号稳定)。"""
        hf = sorted(n for n in self.data if re.fullmatch(r"word/(header|footer)\d*\.xml", n))
        return [DOC, *hf]

    def save(self, path: str) -> None:
        for name, root in self.xml.items():
            self.data[name] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
        names = {i.filename for i in self.infos}
        tmp = f"{path}.tmp"
        with zipfile.ZipFile(tmp, "w") as z:
            for info in self.infos:
                z.writestr(info, self.data[info.filename], compress_type=info.compress_type)
            for name in self.data:
                if name not in names:  # 新加的图片
                    z.writestr(name, self.data[name], compress_type=zipfile.ZIP_DEFLATED)
        os.replace(tmp, path)


def in_fallback(el: etree._Element) -> bool:
    """mc:Fallback 里是同一内容的旧格式副本,Word 不显示,跳过避免重复。"""
    return any(a.tag == MC_FALLBACK for a in el.iterancestors())


def owner_p(el: etree._Element) -> etree._Element | None:
    return next((a for a in el.iterancestors(W_P)), None)


def own_ts(p: etree._Element) -> list[etree._Element]:
    """段落自己的 w:t(不含段内文本框里的段落)。"""
    return [t for t in p.iter(W_T) if owner_p(t) is p and not in_fallback(t)]


def p_text(p: etree._Element) -> str:
    return "".join(t.text or "" for t in own_ts(p))


def own_iter(p: etree._Element, tag: str) -> list[etree._Element]:
    return [e for e in p.iter(tag) if owner_p(e) is p and not in_fallback(e)]


def style_name(doc: Docx, p: etree._Element) -> str:
    """段落样式名(有的模板 styleId 是数字,换成名字才看得懂)。"""
    if not hasattr(doc, "styles"):
        doc.styles = {}
        if "word/styles.xml" in doc.data:
            for st in doc.root("word/styles.xml").findall("w:style", NS):
                n = st.find("w:name", NS)
                if n is not None:
                    doc.styles[st.get(q("w:styleId"))] = n.get(q("w:val"))
    s = p.find("w:pPr/w:pStyle", NS)
    if s is None:
        return ""
    return doc.styles.get(s.get(q("w:val")), s.get(q("w:val")))


def index_doc(doc: Docx) -> tuple[dict, dict, dict]:
    """编号:P=段落(页眉页脚加文件名前缀),T=正文表格,I=正文图片和 Word 图表。顺序即文档顺序。"""
    paras, tables, images = {}, {}, {}
    for part in doc.text_parts():
        prefix = "" if part == DOC else Path(part).stem + ":"
        ps = [p for p in doc.root(part).iter(W_P) if not in_fallback(p)]
        for n, p in enumerate(ps, 1):
            paras[f"{prefix}P{n}"] = p
    root = doc.root(DOC)
    for n, t in enumerate((t for t in root.iter(W_TBL) if not in_fallback(t)), 1):
        tables[f"T{n}"] = t
    blips = [e for e in root.iter(*IMAGE_TAGS) if not in_fallback(e)]
    for n, e in enumerate(blips, 1):
        images[f"I{n}"] = e
    return paras, tables, images


# ---------------------------------------------------------------- extract

def table_rows(tbl: etree._Element) -> list[etree._Element]:
    return tbl.findall(W_TR)


def row_cells(tr: etree._Element) -> list[etree._Element]:
    return tr.findall(W_TC)


def image_size_cm(el: etree._Element) -> str:
    if el.tag != q("v:imagedata"):
        drawing = next(el.iterancestors(q("w:drawing")), None)
        ext = drawing.find(".//wp:extent", NS) if drawing is not None else None
        if ext is not None:
            return f"{int(ext.get('cx')) / EMU_PER_CM:.1f}×{int(ext.get('cy')) / EMU_PER_CM:.1f} cm"
        return "?"
    shape = el.getparent()
    m = dict(re.findall(r"(width|height):([\d.]+)pt", shape.get("style", "")))
    if "width" in m and "height" in m:
        return f"{float(m['width']) / 28.35:.1f}×{float(m['height']) / 28.35:.1f} cm"
    return "?"


def extract(template: str) -> str:
    doc = Docx(template)
    paras, tables, images = index_doc(doc)
    pid = {id(p): k for k, p in paras.items()}
    tid = {id(t): k for k, t in tables.items()}
    iid = {id(e): k for k, e in images.items()}
    out: list[str] = []

    def style(p):
        name = style_name(doc, p)
        return f"[{name}] " if name else ""

    def marks(p):
        tags = []
        if own_iter(p, q("m:oMath")):
            tags.append("〔含公式,不可改〕")
        if own_iter(p, q("w:fldChar")) or own_iter(p, q("w:fldSimple")):
            tags.append("〔含域〕")
        if own_iter(p, q("w:object")):
            tags.append("〔嵌入对象,不可改〕")
        return " ".join(tags)

    def emit_p(p, indent=""):
        text, m = p_text(p), marks(p)
        imgs = [e for tag in IMAGE_TAGS for e in own_iter(p, tag) if id(e) in iid]
        if text.strip() or m or imgs:  # 空段不列
            out.append(f"{indent}{pid[id(p)]} {style(p)}{text} {m}".rstrip())
        for e in imgs:
            kind = "Word 图表(可换成图片)" if e.tag == q("c:chart") else "图片"
            out.append(f"{indent}  {iid[id(e)]} {kind} {image_size_cm(e)}")
        for inner in p.iter(W_P):  # 段内文本框
            if inner is not p and owner_p(inner) is p and id(inner) in pid:
                emit_p(inner, indent + "  〔文本框〕")

    def cell_text(tc):
        parts = [f"{pid[id(p)]} {p_text(p)}".rstrip() for p in tc.findall(W_P) if id(p) in pid]
        tcpr = tc.find(W_TCPR)
        if tcpr is not None:
            span = tcpr.find("w:gridSpan", NS)
            if span is not None:
                parts.append(f"(跨{span.get(q('w:val'))}列)")
            vm = tcpr.find("w:vMerge", NS)
            if vm is not None and vm.get(q("w:val")) != "restart":
                parts.append("(与上格合并)")
        return " / ".join(parts) or "(空)"

    def emit_table(tbl, indent=""):
        rows = table_rows(tbl)
        ncol = max((len(row_cells(r)) for r in rows), default=0)
        out.append(f"{indent}{tid.get(id(tbl), '(页眉页脚表格,不编号)')} 表格 {len(rows)} 行 × {ncol} 列")
        keep = range(len(rows)) if len(rows) <= 12 else [*range(8), *range(len(rows) - 2, len(rows))]
        for i in keep:
            if len(rows) > 12 and i == len(rows) - 2:
                out.append(f"{indent}  … 省略第 8–{len(rows) - 3} 行")
            out.append(f"{indent}  r{i}: " + " | ".join(cell_text(c) for c in row_cells(rows[i])))

    def walk(el, indent=""):
        for child in el:
            if child.tag == W_P:
                emit_p(child, indent)
            elif child.tag == W_TBL:
                emit_table(child, indent)
            elif child.tag in (q("w:sdt"), q("w:sdtContent"), q("w:customXml")):
                walk(child, indent)

    name = Path(template).name
    out.append(f"# 模板文本:{name}")
    out.append(f"段落 {len(paras)} 个,表格 {len(tables)} 个,图片 {len(images)} 张。编号用于填写清单。")
    out.append("")
    walk(doc.root(DOC).find("w:body", NS))
    for part in doc.text_parts()[1:]:
        out.append("")
        out.append(f"## {Path(part).stem}")
        walk(doc.root(part))
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- apply:段落

def set_text(t: etree._Element, text: str) -> None:
    t.text = text
    t.set(XML_SPACE, "preserve")


def replace_in_paragraph(p: etree._Element, find: str, repl: str, all_: bool) -> None:
    ts = own_ts(p)
    full = "".join(t.text or "" for t in ts)
    starts = [m.start() for m in re.finditer(re.escape(find), full)]
    if not starts:
        raise PlanError(f"原文里找不到 {find!r}(段落原文:{full[:80]!r})")
    if len(starts) > 1 and not all_:
        raise PlanError(f"{find!r} 在段内出现 {len(starts)} 次,把 find 写长一点或加 \"all\": true")
    bounds, pos = [], 0
    for t in ts:
        bounds.append((pos, pos + len(t.text or "")))
        pos += len(t.text or "")
    for s in reversed(starts):  # 从后往前,前面的偏移不受影响
        e = s + len(find)
        hit = [i for i, (a, b) in enumerate(bounds) if a < e and b > s or (a == b == s)]
        first, last = hit[0], hit[-1]
        a0, _ = bounds[first]
        al, _ = bounds[last]
        head = (ts[first].text or "")[: s - a0]
        tail = (ts[last].text or "")[e - al:]
        if first == last:
            set_text(ts[first], head + repl + tail)
        else:
            set_text(ts[first], head + repl)
            for i in range(first + 1, last):
                set_text(ts[i], "")
            set_text(ts[last], tail)
        # 偏移按新文本重算,供更靠前的命中使用
        bounds, pos = [], 0
        for t in ts:
            bounds.append((pos, pos + len(t.text or "")))
            pos += len(t.text or "")


def rewrite_paragraph(p: etree._Element, text: str) -> None:
    if own_iter(p, q("w:fldChar")) or own_iter(p, q("w:fldSimple")) or own_iter(p, q("m:oMath")) \
            or own_iter(p, q("w:drawing")) or own_iter(p, q("w:pict")) or own_iter(p, q("w:object")):
        raise PlanError("段内有域/图片/公式/嵌入对象,不能整段重写,改用 find/replace")
    runs = [r for r in p.iter(W_R) if owner_p(r) is p and not in_fallback(r)]
    carrier = next((r for r in runs if r.find(W_T) is not None), runs[0] if runs else None)
    for r in runs:
        for child in list(r):
            if child.tag in TEXT_CHILDREN:
                r.remove(child)
    if carrier is None:
        carrier = etree.SubElement(p, W_R)
    red = carrier.find(f"{W_RPR}/{q('w:color')}")
    if red is not None and (red.get(q("w:val")) or "").upper() == "FF0000":
        red.getparent().remove(red)  # 模板里标红的是"请自行补充"一类提示,填了就恢复正常颜色
    set_text(etree.SubElement(carrier, W_T), text)


def set_cell_text(tc: etree._Element, text: str) -> None:
    ps = tc.findall(W_P)
    if not ps:
        ps = [etree.SubElement(tc, W_P)]
    for extra in ps[1:]:
        tc.remove(extra)
    rewrite_paragraph(ps[0], text)


# ---------------------------------------------------------------- apply:表格

def fmt_cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
        return f"{v:.6g}"
    return str(v)


REF_RE = re.compile(r"\{\{\s*([^{}|]+?)\s*(?:\|([^{}]*))?\}\}")


class Refs:
    """{{字段路径|格式}} 取值。缺数据不报错,填占位,并记下来供报告。"""

    def __init__(self, data: dict | None):
        self.data = data
        self.missing: list[str] = []

    def value(self, path: str):
        if self.data is None:
            raise PlanError(f"用到了 {{{{{path}}}}},但没有数据文件(--data,默认 项目数据结构.json)")
        keys = path.split(".")
        if keys[0] not in self.data:
            raise PlanError(f"数据里没有顶层字段 {keys[0]!r},可选:{list(self.data)}")
        cur = self.data
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return None
            cur = cur[k]
        return cur

    def placeholder(self, path: str) -> str:
        self.missing.append(path)
        return f"【待填写：{path}】"

    def render(self, text: str) -> str:
        def one(m):
            path, spec = m.group(1), m.group(2)
            v = self.value(path)
            if v is None or v == "":
                return self.placeholder(path)
            if isinstance(v, bool):
                if spec is None or ":" not in spec:
                    raise PlanError(f"{path} 是是/否值,格式写成 |满足:不满足")
                yes, no = spec.split(":", 1)
                return yes if v else no
            if spec is None:
                return fmt_cell(v)
            try:
                return format(v, spec)
            except (ValueError, TypeError) as e:
                raise PlanError(f"{path} 的值 {v!r} 不能按 {spec!r} 格式化:{e}")
        return REF_RE.sub(one, text)

    def whole(self, text: str):
        """整个值就是一个引用时返回 (取到的值, 路径);不是引用返回 (text, None)。"""
        m = REF_RE.fullmatch(text.strip())
        if not m:
            return text, None
        return self.value(m.group(1)), m.group(1)


def table_rows_from_json(path: Path, columns: list | None, filters: dict | None = None,
                         scale: dict | None = None) -> list[list[str]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    header, rows = data["header"], data["data"]
    for col, factor in (scale or {}).items():  # 单位换算,如 N/m² → MPa 乘 1e-6
        if col not in header:
            raise PlanError(f"{path.name} 没有列 {col!r},可选列:{header}")
        i = header.index(col)
        rows = [[v * factor if j == i and isinstance(v, (int, float)) and not isinstance(v, bool) else v
                 for j, v in enumerate(r)] for r in rows]
    for col, pattern in (filters or {}).items():  # 按列值正则筛行,如材料表只取混凝土
        if col not in header:
            raise PlanError(f"{path.name} 没有列 {col!r},可选列:{header}")
        i = header.index(col)
        rows = [r for r in rows if re.search(pattern, fmt_cell(r[i]))]
    if columns:
        missing = [c for c in columns if c is not None and c not in header]
        if missing:
            raise PlanError(f"{path.name} 没有列 {missing},可选列:{header}")
        idx = [None if c is None else header.index(c) for c in columns]
        rows = [[None if i is None else r[i] for i in idx] for r in rows]
    return [[fmt_cell(v) for v in r] for r in rows]


def fill_table(tbl: etree._Element, from_row: int, rows: list[list[str]], to_row: int | None) -> None:
    trs = table_rows(tbl)
    end = len(trs) if to_row is None else to_row
    if not 0 <= from_row < end <= len(trs):
        raise PlanError(f"from_row/to_row 超出范围(表格共 {len(trs)} 行)")
    sample = trs[from_row]
    ncell = len(row_cells(sample))
    bad = [i for i, r in enumerate(rows) if len(r) != ncell]
    if bad:
        raise PlanError(f"第 {bad[0]} 行有 {len(rows[bad[0]])} 个值,样板行有 {ncell} 格;用 columns 选列或补齐")
    anchor = sample.getprevious()
    template_row = copy.deepcopy(sample)
    for tr in trs[from_row:end]:
        tbl.remove(tr)
    for values in rows:
        tr = copy.deepcopy(template_row)
        for tc, v in zip(row_cells(tr), values):
            vm = tc.find("w:tcPr/w:vMerge", NS)
            if vm is not None:  # 数据行不纵向合并
                vm.getparent().remove(vm)
            set_cell_text(tc, str(v))
        if anchor is None:
            tbl.insert(tbl.index(tbl.find(q("w:tblGrid"))) + 1, tr)
        else:
            anchor.addnext(tr)
        anchor = tr


# ---------------------------------------------------------------- apply:图片

def replace_image(doc: Docx, el: etree._Element, img_path: Path) -> None:
    from PIL import Image

    if not img_path.is_file():
        raise PlanError(f"图片不存在:{img_path}")
    rels = doc.root("word/_rels/document.xml.rels")
    if el.tag == q("c:chart"):  # Word 图表:新建图片关系,图表的关系和部件留着不用
        n = 1
        while any(r.get("Id") == f"rIdOsisFill{n}" for r in rels):
            n += 1
        rel = etree.SubElement(rels, q("pr:Relationship"))
        rel.set("Id", f"rIdOsisFill{n}")
        rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image")
    else:
        rid = el.get(q("r:embed")) if el.tag == q("a:blip") else el.get(q("r:id"))
        rel = next((r for r in rels if r.get("Id") == rid), None)
        if rel is None:
            raise PlanError(f"找不到图片关系 {rid}")
    ext = img_path.suffix.lower().lstrip(".")
    ext = "jpeg" if ext == "jpg" else ext
    n = 1
    while f"word/media/osis_fill_{n}.{ext}" in doc.data:
        n += 1
    part = f"word/media/osis_fill_{n}.{ext}"
    doc.data[part] = img_path.read_bytes()
    rel.set("Target", f"media/osis_fill_{n}.{ext}")
    ct = doc.root("[Content_Types].xml")
    if not any(d.get("Extension", "").lower() == ext for d in ct.findall("ct:Default", NS)):
        d = etree.SubElement(ct, q("ct:Default"))
        d.set("Extension", ext)
        d.set("ContentType", f"image/{ext}")
    with Image.open(io.BytesIO(doc.data[part])) as im:
        ratio = im.height / im.width
    if el.tag != q("v:imagedata"):  # 宽不变,高按新图比例
        drawing = next(el.iterancestors(q("w:drawing")))
        if el.tag == q("c:chart"):
            chart_to_picture(el, rel.get("Id"), n)
        for e in (*drawing.iter(q("wp:extent")), *drawing.iter(q("a:ext"))):
            if e.get("cx") and e.get("cy"):
                e.set("cy", str(int(int(e.get("cx")) * ratio)))
    else:
        shape = el.getparent()
        style = shape.get("style", "")
        m = re.search(r"width:([\d.]+)pt", style)
        if m:
            h = f"height:{float(m.group(1)) * ratio:.2f}pt"
            style = re.sub(r"height:[\d.]+pt", h, style) if "height:" in style else f"{style};{h}"
            shape.set("style", style)


def chart_to_picture(chart: etree._Element, rid: str, n: int) -> None:
    """把 a:graphicData 里的图表换成引用 rid 的图片,尺寸沿用图表的显示尺寸。"""
    gdata = chart.getparent()
    ext = next(gdata.iterancestors(q("w:drawing"))).find(".//wp:extent", NS)
    gdata.set("uri", NS["pic"])
    for child in list(gdata):
        gdata.remove(child)
    pic = etree.SubElement(gdata, q("pic:pic"))
    nv = etree.SubElement(pic, q("pic:nvPicPr"))
    cnv = etree.SubElement(nv, q("pic:cNvPr"))
    cnv.set("id", "0")
    cnv.set("name", f"osis_fill_{n}")
    etree.SubElement(nv, q("pic:cNvPicPr"))
    fill = etree.SubElement(pic, q("pic:blipFill"))
    etree.SubElement(fill, q("a:blip")).set(q("r:embed"), rid)
    etree.SubElement(etree.SubElement(fill, q("a:stretch")), q("a:fillRect"))
    sppr = etree.SubElement(pic, q("pic:spPr"))
    xfrm = etree.SubElement(sppr, q("a:xfrm"))
    off = etree.SubElement(xfrm, q("a:off"))
    off.set("x", "0")
    off.set("y", "0")
    aext = etree.SubElement(xfrm, q("a:ext"))
    aext.set("cx", ext.get("cx"))
    aext.set("cy", ext.get("cy"))
    etree.SubElement(etree.SubElement(sppr, q("a:prstGeom"), prst="rect"), q("a:avLst"))


def image_to_placeholder(el: etree._Element, text: str) -> None:
    """本项目没有这张图:去掉模板里的旧图,原位置写占位文字。"""
    run = next(el.iterancestors(W_R))
    new = etree.Element(W_R)
    set_text(etree.SubElement(new, W_T), text)
    run.addprevious(new)
    run.getparent().remove(run)


# ---------------------------------------------------------------- apply:占位标红、更新域

def color_red(r: etree._Element) -> None:
    rpr = r.find(W_RPR)
    if rpr is None:
        rpr = etree.Element(W_RPR)
        r.insert(0, rpr)
    old = rpr.find(q("w:color"))
    if old is not None:
        rpr.remove(old)
    color = etree.Element(q("w:color"))
    color.set(q("w:val"), "FF0000")
    after = next((c for c in rpr if c.tag in AFTER_COLOR), None)
    if after is not None:
        after.addprevious(color)
    else:
        rpr.append(color)


def mark_placeholders(doc: Docx) -> int:
    """把【待填写：…】拆成独立的 run 并标红。返回个数。"""
    count = 0
    for part in doc.text_parts():
        for t in list(doc.root(part).iter(W_T)):
            text = t.text or ""
            if not PLACEHOLDER_RE.search(text):
                continue
            r = t.getparent()
            pieces = [s for s in re.split(f"({PLACEHOLDER_RE.pattern})", text) if s]
            count += sum(1 for s in pieces if PLACEHOLDER_RE.fullmatch(s))
            if len(pieces) == 1:
                color_red(r)
                continue
            rest = list(t.itersiblings())  # t 之后的子元素随最后一段走
            set_text(t, pieces[0])
            if PLACEHOLDER_RE.fullmatch(pieces[0]):
                color_red(r)
            prev = r
            for s in pieces[1:]:
                nr = etree.Element(W_R)
                if r.find(W_RPR) is not None:
                    nr.append(copy.deepcopy(r.find(W_RPR)))
                    old = nr.find(f"{W_RPR}/{q('w:color')}")
                    if old is not None and not PLACEHOLDER_RE.fullmatch(s) and PLACEHOLDER_RE.fullmatch(pieces[0]):
                        old.getparent().remove(old)  # 原 run 被标红了,后续普通文字去掉红色
                set_text(etree.SubElement(nr, W_T), s)
                if PLACEHOLDER_RE.fullmatch(s):
                    color_red(nr)
                prev.addnext(nr)
                prev = nr
            for child in rest:
                prev.append(child)
    return count


def set_update_fields(doc: Docx) -> None:
    """让 Word 打开时更新目录、页码、题注编号。"""
    name = "word/settings.xml"
    if name not in doc.data:
        return
    root = doc.root(name)
    if root.find(q("w:updateFields")) is not None:
        return
    el = etree.Element(q("w:updateFields"))
    el.set(q("w:val"), "true")
    after = next((c for c in root if c.tag in AFTER_UPDATE_FIELDS), None)
    if after is not None:
        after.addprevious(el)
    else:
        root.append(el)


# ---------------------------------------------------------------- apply

def apply(template: str, plan_path: str, output: str, base_dir: Path, data_path: Path | None = None) -> int:
    doc = Docx(template)
    if data_path is None and (base_dir / "项目数据结构.json").is_file():
        data_path = base_dir / "项目数据结构.json"
    refs = Refs(json.loads(data_path.read_text(encoding="utf-8-sig")) if data_path else None)
    paras, tables, images = index_doc(doc)
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8-sig"))
    if not isinstance(plan, list):
        raise SystemExit("填写清单必须是 JSON 列表")
    errors: list[str] = []
    touched: set[int] = set()
    applied = 0

    def resolve(p: str) -> Path:
        path = Path(p)
        return path if path.is_absolute() else base_dir / path

    for n, op in enumerate(plan, 1):
        tag = op.get("id") or op.get("table") or op.get("image") or "?"
        try:
            if "table" in op:
                tbl = tables.get(op["table"])
                if tbl is None:
                    raise PlanError("没有这个表格编号")
                if op.get("keep"):
                    touched.update(id(p) for p in tbl.iter(W_P))
                    applied += 1
                    continue
                from_row = int(op.get("from_row", 1))
                rows = op.get("rows")
                if rows is None:
                    if "json" not in op:
                        raise PlanError("表格操作要给 rows 或 json")
                    src, ref = refs.whole(str(op["json"]))
                    if src is None:  # 本项目没有这张表的数据
                        ncell = len(row_cells(table_rows(tbl)[from_row])) if from_row < len(table_rows(tbl)) else 1
                        rows = [[refs.placeholder(ref)] + [""] * (ncell - 1)]
                    else:
                        rows = table_rows_from_json(resolve(str(src)), op.get("columns"), op.get("filter"), op.get("scale"))
                        if not rows:
                            ncell = len(row_cells(table_rows(tbl)[from_row]))
                            rows = [[refs.placeholder(f"{ref or src} 无符合条件的行")] + [""] * (ncell - 1)]
                rows = [[refs.render(fmt_cell(v)) for v in r] for r in rows]
                touched.update(id(p) for p in tbl.iter(W_P))  # 整表算已处理(含被删的原数据行)
                fill_table(tbl, from_row, rows, op.get("to_row"))
            elif "image" in op:
                el = images.get(op["image"])
                if el is None:
                    raise PlanError("没有这个图片编号")
                src, ref = refs.whole(str(op["path"]))
                if src is None:
                    image_to_placeholder(el, refs.placeholder(ref))
                else:
                    replace_image(doc, el, resolve(str(src)))
            else:
                p = paras.get(op.get("id", ""))
                if p is None:
                    raise PlanError("没有这个段落编号")
                if op.get("keep"):
                    pass
                elif "text" in op:
                    rewrite_paragraph(p, refs.render(str(op["text"])))
                elif "find" in op:
                    if "replace" not in op:
                        raise PlanError("find 要配 replace")
                    replace_in_paragraph(p, str(op["find"]), refs.render(str(op["replace"])), bool(op.get("all")))
                else:
                    raise PlanError("不认识的操作,见脚本开头说明")
                touched.add(id(p))
            applied += 1
        except PlanError as e:
            errors.append(f"第 {n} 条 [{tag}]:{e}")

    if errors:
        print(f"清单有 {len(errors)} 处错误,未生成文件:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    placeholders = mark_placeholders(doc)
    set_update_fields(doc)
    doc.save(output)

    # 表格里的按表汇总,免得逐格列出
    tid = {id(t): k for k, t in tables.items()}
    leftovers, table_left = [], {}
    for k, p in paras.items():
        if id(p) in touched or not re.search(r"\d", p_text(p)) or style_name(doc, p).lower().startswith("toc"):
            continue  # 目录是域,Word 打开时更新
        tbl = next((a for a in p.iterancestors(W_TBL)), None)
        if tbl is not None and id(tbl) in tid:
            table_left[tid[id(tbl)]] = table_left.get(tid[id(tbl)], 0) + 1
        else:
            leftovers.append(f"  {k} {p_text(p)[:60]}")
    leftovers += [f"  {k} 表内 {n} 格含数字" for k, n in table_left.items()]
    print(f"已生成:{output}")
    print(f"执行 {applied} 条,占位【待填写】{placeholders} 处。")
    if refs.missing:
        print(f"\n本项目无数据、已填占位的字段 {len(refs.missing)} 个(核对字段名是否写对):")
        print("\n".join(f"  {m}" for m in dict.fromkeys(refs.missing)))
    if leftovers:
        print(f"\n未处理且含数字的段落 {len(leftovers)} 个(逐个确认:本项目的数改掉或占位,通用内容加 keep):")
        print("\n".join(leftovers[:150]))
        if len(leftovers) > 150:
            print(f"  …另有 {len(leftovers) - 150} 个")
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="在 DOCX 计算书模板上原位填写本项目数据")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("extract", help="列出模板全部文字和编号")
    ex.add_argument("template")
    ex.add_argument("-o", "--output", required=True)
    ap_ = sub.add_parser("apply", help="按填写清单生成计算书")
    ap_.add_argument("template")
    ap_.add_argument("plan")
    ap_.add_argument("-o", "--output", required=True)
    ap_.add_argument("--base", default=".", help="清单里 json/图片相对路径的起点,默认当前目录(项目根目录)")
    ap_.add_argument("--data", help="{{字段}} 的数据来源,默认 <base>/项目数据结构.json")
    args = ap.parse_args()
    if args.cmd == "extract":
        Path(args.output).write_text(extract(args.template), encoding="utf-8")
        print(f"已输出:{args.output}")
        return 0
    if Path(args.output).resolve() == Path(args.template).resolve():
        raise SystemExit("输出不能覆盖模板")
    return apply(args.template, args.plan, args.output, Path(args.base), Path(args.data) if args.data else None)


if __name__ == "__main__":
    sys.exit(main())
