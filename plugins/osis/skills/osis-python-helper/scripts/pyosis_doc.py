#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pyosis API docstring 查找 CLI（运行时从已安装 pyosis 反射，不读大 manager.py）。

用法:
  python pyosis_doc.py version
  python pyosis_doc.py lookup create_line_load
  python pyosis_doc.py lookup LoadCase.create_line_load
  python pyosis_doc.py lookup UTEMP
  python pyosis_doc.py lookup "load.create UTEMP"
  python pyosis_doc.py lookup create --all
  python pyosis_doc.py search line
  python pyosis_doc.py search uniform --limit 20
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import pkgutil
import re
import sys
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ApiEntry:
    short: str
    qual: str  # Class.method 或 module.func
    module: str
    obj: Any
    kind: str  # method | function | class

    @property
    def keys(self) -> tuple[str, ...]:
        parts = [self.short, self.qual, f"{self.module}.{self.qual}"]
        # 兼容 engine.xxx 口语: material.create_conc
        if "." in self.qual:
            parts.append(self.qual.lower())
        return tuple(dict.fromkeys(parts))  # 保序去重


_INDEX: list[ApiEntry] | None = None


def _is_pyosis_class(obj: Any, module_name: str) -> bool:
    return inspect.isclass(obj) and getattr(obj, "__module__", "").startswith("pyosis")


def _public_callables(obj: Any) -> Iterable[tuple[str, Any]]:
    for name, member in inspect.getmembers(obj):
        if name.startswith("_"):
            continue
        if inspect.isroutine(member) or isinstance(member, (staticmethod, classmethod)):
            yield name, member


def _unwrap(obj: Any) -> Any:
    return inspect.unwrap(obj) if callable(obj) else obj


def build_index() -> list[ApiEntry]:
    import pyosis

    entries: list[ApiEntry] = []
    seen: set[tuple[str, str]] = set()

    def add(short: str, qual: str, module: str, obj: Any, kind: str) -> None:
        key = (module, qual)
        if key in seen:
            return
        seen.add(key)
        entries.append(ApiEntry(short=short, qual=qual, module=module, obj=obj, kind=kind))

    # 覆盖 manager / engine / 少量 interface
    for info in pkgutil.walk_packages(pyosis.__path__, pyosis.__name__ + "."):
        name = info.name
        if not (
            name.endswith(".manager")
            or name.endswith(".engine")
            or name.endswith(".interface")
            or name.endswith(".static")
        ):
            continue
        try:
            mod = importlib.import_module(name)
        except Exception:
            continue

        for cname, cls in inspect.getmembers(mod, predicate=lambda o: _is_pyosis_class(o, name)):
            if cls.__module__ != name and not cls.__module__.startswith("pyosis"):
                continue
            # 类本身
            add(cname, cname, cls.__module__, cls, "class")
            for mname, member in _public_callables(cls):
                try:
                    raw = cls.__dict__.get(mname, member)
                    target = _unwrap(raw if not isinstance(raw, (staticmethod, classmethod)) else raw.__func__)
                except Exception:
                    target = member
                add(mname, f"{cname}.{mname}", cls.__module__, target, "method")

            # @property / dataclass 字段(读回常用,如 LoadCase.gradient_temp)
            for pname, prop in inspect.getmembers(cls, predicate=lambda o: isinstance(o, property)):
                if pname.startswith("_"):
                    continue
                add(pname, f"{cname}.{pname}", cls.__module__, prop, "property")
            fields = getattr(cls, "__dataclass_fields__", None)
            if fields:
                for fname in fields:
                    if fname.startswith("_"):
                        continue
                    # 用 class 上的 field 对象占位;doc 用 dataclass 字段注释有限
                    add(fname, f"{cname}.{fname}", cls.__module__, cls, "field")

        for fname, func in inspect.getmembers(mod, inspect.isfunction):
            if fname.startswith("_"):
                continue
            if func.__module__ != name:
                continue
            add(fname, fname, name, func, "function")

    return entries


def get_index() -> list[ApiEntry]:
    global _INDEX
    if _INDEX is None:
        _INDEX = build_index()
    return _INDEX


def _doc_first_line(doc: str | None) -> str:
    if not doc:
        return ""
    for line in doc.strip().splitlines():
        s = line.strip()
        if s:
            return s
    return ""


def _format_entry(entry: ApiEntry, *, full: bool) -> str:
    obj = entry.obj
    lines = [
        f"=== {entry.qual} ===",
        f"kind: {entry.kind}",
        f"module: {entry.module}",
    ]
    try:
        if entry.kind == "class":
            lines.append(f"signature: class {entry.short}(...)")
        elif entry.kind == "field":
            lines.append("signature: <dataclass field / readback attribute>")
        elif entry.kind == "property":
            try:
                lines.append(f"signature: @property {inspect.signature(entry.obj.fget)}")
            except Exception:
                lines.append("signature: @property")
        else:
            lines.append(f"signature: {inspect.signature(obj)}")
    except (TypeError, ValueError) as e:
        lines.append(f"signature: <unavailable: {e}>")

    try:
        src = inspect.getsourcefile(obj) or inspect.getfile(obj)
        _, lineno = inspect.getsourcelines(obj)
        lines.append(f"source: {src}:{lineno}")
    except Exception:
        pass

    # 覆盖 docstring 易误导处(实测/模板口径)
    if entry.qual == "PropertyManager.assign_component_thickness":
        lines.append(
            "hint: L0 改厚度用 op='a'(与模板一致)。"
            "docstring 的 's'=替换在部分 OSIS 上会报「编辑构件厚度有误」。"
        )
    if entry.qual == "LoadCase.create_gradient_temperature":
        lines.append(
            "hint: 读回用 lc.gradient_temp,按 entityNO==目标单元过滤单条;"
            "禁止 print 全表。改顶板温差通常只动第一段 t1,其余从现网/prep 原样抄回。"
        )
    if entry.qual == "TendonPropManager.create":
        lines.append(
            "hint: 便捷入口未展开摩阻位序。模板常见 IN+规范面积 → 再 lookup create_in;"
            "friction_coeff / deviation_coeff 在 create_in 里是 pipe 之后的第 1、2 个可选位置参数。"
        )
    if entry.qual == "TendonPropManager.create_in":
        lines.append(
            "hint: 位置序 name,mat,code,diameter,num,pipe,"
            "friction_coeff,deviation_coeff,starting_deform,end_deform,tensioning_coeff,relaxation_coeff。"
            "prep 例: create('15-21','IN',5,1,'GBT5224_2014',15.2,21,0.1, 摩阻, 偏差, ...)"
            "——注意便捷 create 参数序是 name,s_type,mat,area 再接 create_in 余参。"
        )
    if entry.qual in ("LoadCase.gradient_temp",) or (
        entry.kind == "field" and entry.qual.endswith(".gradient_temp")
    ):
        lines.append(
            "hint: list[dict];用 next(x for x in lc.gradient_temp if x['entityNO']==N) 取单条。"
        )

    doc = inspect.getdoc(obj) or ""
    if full:
        lines.append("docstring:")
        lines.append(doc if doc else "<empty>")
    else:
        head = _doc_first_line(doc)
        if head:
            lines.append(f"summary: {head}")
    return "\n".join(lines)


# LoadCase.create("TYPE", ...) → 具体 create_* 映射(与 pyosis LoadCase.create 一致)
LOAD_TYPE_TO_QUAL: dict[str, str] = {
    "GRAVITY": "LoadCase.create_gravity",
    "NFORCE": "LoadCase.create_nforce",
    "LINE": "LoadCase.create_line_load",
    "DISPLACEMENT": "LoadCase.create_displacement",
    "INITIAL": "LoadCase.create_initial_force",
    "UTEMP": "LoadCase.create_uniform_temperature",
    "GTEMP": "LoadCase.create_gradient_temperature",
    "PST": "LoadCase.create_prestress",
    "CFORCE": "LoadCase.create_cable_force",
    "CONCENTRATED": "LoadCase.create_concentrated_force",
    "SURFACE": "LoadCase.create_surface_load",
    "SURFACE_VEC": "LoadCase.create_surface_load_vector",
}

# 口语路径 → 限定名
PATH_ALIASES: dict[str, str] = {
    "load.create": "LoadCase.create",
    "engine.load.create": "LoadCase.create",
    "lc.create": "LoadCase.create",
    "loadcase.create": "LoadCase.create",
    "load.get": "LoadCaseManager.get",
    "engine.load.get": "LoadCaseManager.get",
    "lc.get": "LoadCaseManager.get",
    # 两级: engine.tendon.prop.create / tendon.prop.create
    "tendon.prop.create": "TendonPropManager.create",
    "engine.tendon.prop.create": "TendonPropManager.create",
    "tendon.prop.create_in": "TendonPropManager.create_in",
    "engine.tendon.prop.create_in": "TendonPropManager.create_in",
    "tendon.prop.create_in_custom": "TendonPropManager.create_in_custom",
    "tendon.prop.create_ex": "TendonPropManager.create_ex",
    "tendon.prop.create_ex_custom": "TendonPropManager.create_ex_custom",
    "tendon.shape.create": "TendonShapeManager.create",
    "engine.tendon.shape.create": "TendonShapeManager.create",
}

# engine.xxx / 短前缀 → Manager 类名(用于 prop.assign_* 等)
MANAGER_PREFIX: dict[str, str] = {
    "prop": "PropertyManager",
    "property": "PropertyManager",
    "material": "MaterialManager",
    "section": "SectionManager",
    "node": "NodeManager",
    "element": "ElementManager",
    "boundary": "BoundaryManager",
    "stage": "StageManager",
    "settlement": "SettlementManager",
    "control": "ControlManager",
    "geometry": "GeometryManager",
    "project": "ProjectManager",
    "thickness": "ThicknessManager",
    "live": "LiveCaseManager",
    "load": "LoadCaseManager",
}

# 嵌套前缀: tendon.prop → TendonPropManager
NESTED_PREFIX: dict[tuple[str, ...], str] = {
    ("tendon", "prop"): "TendonPropManager",
    ("tendon", "shape"): "TendonShapeManager",
}


def _expand_manager_path(token: str) -> list[str]:
    """prop.assign_* / tendon.prop.create → 对应 Manager.method"""
    parts = [p for p in token.split(".") if p]
    if len(parts) < 2:
        return []
    out: list[str] = []
    # 去掉可选 engine. 前缀
    if parts[0].lower() == "engine":
        parts = parts[1:]
    if len(parts) < 2:
        return []

    # 两级嵌套: tendon.prop.create
    key2 = (parts[0].lower(), parts[1].lower())
    if key2 in NESTED_PREFIX and len(parts) >= 3:
        out.append(f"{NESTED_PREFIX[key2]}.{'.'.join(parts[2:])}")
        return out

    head = parts[0].lower()
    if head in MANAGER_PREFIX:
        out.append(f"{MANAGER_PREFIX[head]}.{'.'.join(parts[1:])}")
    return out


def _normalize_tokens(query: str) -> list[str]:
    """把 'load.create UTEMP' / 'prop.assign_*' / 短名 拆成可查 token。"""
    raw = query.strip()
    if not raw:
        return []
    parts = [p for p in re.split(r"[\s,;/|]+", raw) if p]
    out: list[str] = []
    for p in parts:
        out.append(p)
        pl = p.lower().replace(" ", "")
        if pl in PATH_ALIASES:
            out.append(PATH_ALIASES[pl])
        out.extend(_expand_manager_path(p))
        if pl.endswith(".create") and pl not in PATH_ALIASES and "load" in pl:
            out.append("LoadCase.create")
    return out


def _alias_queries(query: str) -> tuple[list[str], str | None]:
    """返回(查询列表, 可选 tip)。优先展开荷载 TYPE。"""
    tokens = _normalize_tokens(query)
    tip = None
    queries: list[str] = []

    type_hits = [t.upper() for t in tokens if t.upper() in LOAD_TYPE_TO_QUAL]
    if type_hits:
        t = type_hits[0]
        qual = LOAD_TYPE_TO_QUAL[t]
        queries.append(qual)
        tip = (
            f"hint: prep 常用 lc.create({t!r}, ...); "
            f"内部转发到 {qual}。查参数请看该 create_* 的 docstring。"
        )
        # 附带底层 static 函数(若有)
        for e in get_index():
            if t.lower() in e.short.lower() and e.module.endswith(".static"):
                queries.append(e.qual)
        return list(dict.fromkeys(queries)), tip

    for t in tokens:
        tl = t.lower().replace(" ", "")
        if tl in PATH_ALIASES:
            queries.append(PATH_ALIASES[tl])
        queries.append(t)
    # 原始整串也试一次(兼容 Class.method)
    queries.insert(0, query.strip())
    return list(dict.fromkeys(queries)), tip


def _match_entries(query: str, *, search_docs: bool = False) -> list[ApiEntry]:
    q = query.strip()
    if not q:
        return []
    q_lower = q.lower()
    idx = get_index()

    exact: list[ApiEntry] = []
    suffix: list[ApiEntry] = []
    contains: list[ApiEntry] = []
    in_doc: list[ApiEntry] = []

    for e in idx:
        keys_l = [k.lower() for k in e.keys]
        if q_lower in keys_l:
            exact.append(e)
            continue
        if any(k == q_lower or k.endswith("." + q_lower) for k in keys_l):
            suffix.append(e)
            continue
        if any(q_lower in k for k in keys_l):
            contains.append(e)
            continue
        if search_docs:
            doc = (inspect.getdoc(e.obj) or "").lower()
            if q_lower in doc:
                in_doc.append(e)

    out: list[ApiEntry] = []
    seen: set[tuple[str, str]] = set()
    for group in (exact, suffix, contains, in_doc):
        for e in group:
            key = (e.module, e.qual)
            if key not in seen:
                seen.add(key)
                out.append(e)
    return out


def _resolve_hits(query: str, *, search_docs: bool) -> tuple[list[ApiEntry], str | None]:
    queries, tip = _alias_queries(query)
    hits: list[ApiEntry] = []
    seen: set[tuple[str, str]] = set()
    for q in queries:
        for e in _match_entries(q, search_docs=search_docs):
            key = (e.module, e.qual)
            if key not in seen:
                seen.add(key)
                hits.append(e)
        # 别名已精确命中 create_* 时,不必再搜宽
        if tip and hits:
            break
    return hits, tip


def cmd_version(_: argparse.Namespace) -> None:
    import pyosis

    print(f"pyosis {pyosis.__version__}")
    print(f"file   {pyosis.__file__}")
    print(f"index  {len(get_index())} entries")


def cmd_lookup(args: argparse.Namespace) -> None:
    hits, tip = _resolve_hits(args.query, search_docs=False)
    if not hits:
        print(f"FAIL: 未找到 {args.query!r}", file=sys.stderr)
        print(
            "tip: 试短名 `assign_component_thickness`、TYPE `UTEMP`、或 `search <子串>`",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if tip:
        print(tip)

    # 精确优先：short 或 qual 完全相等(对展开后的查询)
    q_candidates = {q.lower() for q in _alias_queries(args.query)[0]}
    exact = [
        e
        for e in hits
        if e.short.lower() in q_candidates or e.qual.lower() in q_candidates
    ]
    chosen = exact if exact else hits

    # 荷载 TYPE 别名命中时,默认只展开主 create_*(第一个)
    if tip and not args.all:
        chosen = chosen[:1]

    if len(chosen) > 1 and not args.all:
        print(f"FOUND {len(chosen)} candidates for {args.query!r} (用 --all 展开全部,或改用 Class.method):")
        for e in chosen[: args.limit]:
            print(f"  - {e.qual:40}  [{e.module}]  {_doc_first_line(inspect.getdoc(e.obj))}")
        if len(chosen) > args.limit:
            print(f"  ... +{len(chosen) - args.limit} more")
        raise SystemExit(2)

    for i, e in enumerate(chosen if args.all else chosen[:1]):
        if i:
            print()
        print(_format_entry(e, full=True))


def cmd_search(args: argparse.Namespace) -> None:
    hits, tip = _resolve_hits(args.query, search_docs=True)
    if not hits:
        print(f"FAIL: 未找到含 {args.query!r} 的 API", file=sys.stderr)
        raise SystemExit(1)
    if tip:
        print(tip)
    print(f"FOUND {len(hits)} for {args.query!r}:")
    for e in hits[: args.limit]:
        print(f"  - {e.qual:40}  [{e.module}]  {_doc_first_line(inspect.getdoc(e.obj))}")
    if len(hits) > args.limit:
        print(f"  ... +{len(hits) - args.limit} more (提高 --limit 查看)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="pyosis 函数名 → signature + docstring 查找")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("version", help="显示 pyosis 版本与索引规模")
    s.set_defaults(func=cmd_version)

    s = sub.add_parser("lookup", help="按函数名/Class.method 查完整 docstring")
    s.add_argument("query")
    s.add_argument("--all", action="store_true", help="同名多命中时全部展开")
    s.add_argument("--limit", type=int, default=30, help="候选列表上限")
    s.set_defaults(func=cmd_lookup)

    s = sub.add_parser("search", help="子串搜索 API 名")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_search)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
