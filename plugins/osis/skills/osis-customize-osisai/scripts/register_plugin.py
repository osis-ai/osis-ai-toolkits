# -*- coding: utf-8 -*-
"""plugins.json 注册/删除工具。

本脚本以 UTF-8 读写文件,绕开各种字符的坑,
并在写回后自校验 JSON 合法性。

用法(bash,中文参数用单引号包住即可):
  注册新插件:
    python <skill_dir>/scripts/register_plugin.py add \
        --name '单位换算器' --dir unitconv \
        --desc '单位换算:长度与温度单位互转' \
        --detail 'GUI:选类别与单位,输数值点转换。命令行:...\\unitconv\\main.py 100 m mm 输出 100000'
  覆盖已有条目(改插件后重新注册):同上,加 --replace
  删除条目(删插件时用):
    python <skill_dir>/scripts/register_plugin.py remove --dir unitconv

add 自动生成:icon = <dir>/icon.png,cmd = <dir>/main.py。
remove 按 icon/cmd 的目录前缀匹配整条删除。
"""
import argparse
import json
import sys
from pathlib import Path

# 用户插件清单只在用户态,不在安装包 opencode\
PLUGINS_JSON = Path.home() / ".osisai" / "plugins" / "plugins.json"


def _dir_of(entry: dict) -> str:
    """取条目指向的插件目录名(cmd/icon 路径的第一段)。"""
    for key in ("cmd", "icon"):
        parts = str(entry.get(key, "")).replace("\\", "/").split("/")
        if parts and parts[0]:
            return parts[0]
    return ""


def _load() -> list:
    with open(PLUGINS_JSON, encoding="utf-8") as f:
        return json.load(f)


def _save(data: list) -> None:
    with open(PLUGINS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(PLUGINS_JSON, encoding="utf-8") as f:  # 写回后自校验
        json.load(f)


def cmd_add(ns: argparse.Namespace) -> int:
    data = _load()
    dup = [i for i, e in enumerate(data) if e.get("name") == ns.name or _dir_of(e) == ns.dir]
    if dup and not ns.replace:
        who = ", ".join(f"第{i + 1}条({data[i].get('name')})" for i in dup)
        print(f"错误: 已存在 name={ns.name!r} 或目录 {ns.dir} 的条目 [{who}];覆盖请加 --replace", file=sys.stderr)
        return 1
    entry = {
        "name": ns.name,
        "icon": f"{ns.dir}/icon.png",
        "desc": ns.desc,
        "detail": ns.detail,
        "cmd": f"{ns.dir}/main.py",
    }
    if dup:  # --replace:原地替换第一条,其余重复删掉,保持列表顺序不变
        first = dup[0]
        data = [e for i, e in enumerate(data) if i not in set(dup)]
        data.insert(first, entry)
    else:
        data.append(entry)
    _save(data)
    print(f"已注册 {ns.dir}(共 {len(data)} 条)")
    return 0


def cmd_remove(ns: argparse.Namespace) -> int:
    data = _load()
    kept = [e for e in data if _dir_of(e) != ns.dir]
    if len(kept) == len(data):
        print(f"错误: plugins.json 里没有目录 {ns.dir} 的条目", file=sys.stderr)
        return 1
    _save(kept)
    print(f"已删除 {ns.dir} 条目(剩 {len(kept)} 条)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="register_plugin", description="plugins.json 注册/删除工具")
    sub = parser.add_subparsers(dest="op", required=True)

    p_add = sub.add_parser("add", help="注册/覆盖插件条目")
    p_add.add_argument("--name", required=True, help="中文显示名(图标文字取它第一个字)")
    p_add.add_argument("--dir", required=True, help="插件英文目录名")
    p_add.add_argument("--desc", required=True, help="一句话功能")
    p_add.add_argument("--detail", required=True, help="用法详情:GUI 用法 + CLI 实际命令与示例")
    p_add.add_argument("--replace", action="store_true", help="已存在同名/同目录条目时覆盖而非报错")
    p_add.set_defaults(fn=cmd_add)

    p_rm = sub.add_parser("remove", help="删除插件条目")
    p_rm.add_argument("--dir", required=True, help="插件英文目录名")
    p_rm.set_defaults(fn=cmd_remove)

    ns = parser.parse_args()
    try:
        return ns.fn(ns)
    except OSError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
