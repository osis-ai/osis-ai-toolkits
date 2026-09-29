"""main.py — 入口脚本,按 _1.._10 顺序依次执行 prep 模块。

可直接 `python main.py`,或被 import 后调 main()。
engine 用 _0_engine 模块级单例,跟同包内的 prep 模块保持一致。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 让 main.py 不管从哪个目录跑都能 import 同目录的 prep modules
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pyosis import batch
from _0_engine import engine
from _1_control import setup_control
from _2_property import build_property
from _3_material import build_materials
from _4_section import build_sections
from _5_node import build_nodes
from _6_element import build_elements
from _7_boundary import build_boundaries
from _8_loadcase import build_loadcases
from _9_analysis import build_analysis
from _10_stage import build_stages

def main() -> None:
    with batch():
        engine.clear()
        engine.clc()

        setup_control(engine)
        build_property(engine)
        build_materials(engine)
        build_sections(engine)
        build_nodes(engine)
        build_elements(engine)
        build_boundaries(engine)
        build_loadcases(engine)
        build_analysis(engine)
        build_stages(engine)

if __name__ == "__main__":
    main()
