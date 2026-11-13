---
name: osis-module-section
description: 截面建模模块。生成 `prep/_4_section.py`,创建截面、设置偏移与网格,以及变截面组 TaperEle。截面方案(类型、尺寸)由桥型层决定。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-section

> `prep/_4_section.py`:`build_sections(engine)`。有哪些截面类型、各自参数用 `api_grep "def create_" section` / `api_read` 查。

## 创建

- **显式传 `no`(第一个位置参数)**:自动分配会让 `_6` 的引用错位,也没法同号覆盖重跑。
- 参数化 `create_<类型>` 优先,表达不了才用 `create_custom`。
- **改尺寸要联动**:参数化截面从目标尺寸反推全部几何参数,只改 `h` 会报"该参数组合几何检查不通过";自定义截面逐点变换 `contour_matrix`,整体按比例缩放会把板厚、倒角一起缩。做法见 `references/section_transform.md`。
- 坐标约定:Y=0 在截面横向中心,Z=0 在顶面,Z 向下为负。

## 偏移与网格

每个截面创建后都要设:

```python
sec.set_offset(
    offset_type_y="Middle",    # "Left"/"Middle"/"Right"/"Manual"
    offset_value_y=0.0,
    offset_type_z="Top",       # "Top"/"Center"/"Bottom"/"Manual"
    offset_value_z=0.0,
)
sec.set_mesh(1, 0, 0.1)        # part_id, mesh_method, mesh_size
```

- **`offset_type_z` 默认是 `"Center"`**;主梁按顶缘对齐要显式传 `"Top"`。
- `set_mesh` 的参数名是 `mesh_method`(不是 `method`)。`part_id` 混凝土截面填 1、模板组合截面填 2;`mesh_method` 0=自动 / 1=手动;`mesh_size` 只在手动时起作用。模板统一写 `set_mesh(1, 0, 0.1)`。
- 中梁/边梁的 y 偏移由截面 API 的梁位参数给(各 API 名字和取值大小写不同,如 `e_girder_pos` / `girder_pos`,以 `api_read` 为准)。梁位参数和 `set_offset` 只在一处设 y 偏移,不要重复。

## 变截面组(TaperEle)

由 OSIS 在两端截面之间自动生成中间截面,不用手建。两个条件都满足才能用:

- 参数化截面(L 型、T 型、工字型、圆/圆管、矩形、圆端形、小箱梁、T 梁、常规箱梁)。**不支持 `create_custom`**。
- 整组单元的 `sec1`/`sec2`、`z_trans`、`y_trans` 一致。

```python
engine.element.taper_group.create(
    "变截面-左", 1, 2.0, 0, 0.0,   # name, z_type(0 线性/1 多项式), z_trans(多项式指数), z_pos(0=I 端/1=J 端), z_dis
    0, 1.0, 0, 0.0,                # y_type, y_trans, y_pos, y_dis
    "3to18",                       # *eles:单号 varargs 或 "5to10" 区间
)
```

- `*eles` 是 varargs,前 9 个参数全位置传。
- 组只覆盖变截段,不含两侧等截面段。
- 同名重复创建是覆盖。
- 生成的中间截面命名如 `408_组1_408`;导出命令流时 TaperEle 被注释,用这些独立截面替代。
- 只有单个单元内部变高时,`create_beam3d(..., z_trans=2)` 即可,不必建组。
- **抛物线凹向由 `z_pos` 决定**(该端斜率为 0):`z_pos` 在浅端 → 梁底朝上凹(墩顶加深的连续梁常用,浅→深段 `z_pos=0`、深→浅段 `z_pos=1`);在深端 → 梁底朝下鼓。
