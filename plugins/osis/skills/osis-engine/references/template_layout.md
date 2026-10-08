# 模板目录布局

所有桥型同一套目录。每份在该桥型 SKILL 的 `references/templates/<目录名>/`(平铺,没有 `<桥型>/<跨径>` 两级)。完整建模先 WeKnora `download_bridge_template` 落到当前工程 `py/`;WeKnora 失效再 `seedtpl` 从本目录复制。

```
<template>/
├── 项目画像.md
└── prep/
    ├── _0_engine.py      # 模块级单例 OSISEngine
    ├── _1_control.py     # setup_control(engine)
    ├── _2_property.py    # build_property(engine)
    ├── _3_material.py    # build_materials(engine)
    ├── _4_section.py     # build_sections(engine)
    ├── _5_node.py        # build_nodes(engine)
    ├── _6_element.py     # build_elements(engine)
    ├── _7_boundary.py    # build_boundaries(engine)
    ├── _8_loadcase.py    # build_loadcases(engine)(含钢束)
    ├── _9_analysis.py    # build_analysis(engine)
    ├── _10_stage.py      # build_stages(engine)
    └── main.py
```

入口是 `prep/main.py`:按序 `from _N import <builder>` 再 `builder(engine)`。`_1` 用 `setup_control`,其余是 `build_*`。

`main.py` 与 `_N_xxx.py` 自带 `sys.path` 引导,**不需要 `cd`**。跑 `python <project_dir>/py/prep/main.py`。
