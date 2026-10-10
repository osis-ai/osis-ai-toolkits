---
name: osis-module-section
description: 截面建模模块。生成 `prep/_4_section.py`,负责创建截面、设置偏移与网格、决定截面编号供下游单元引用。处理箱梁/矩形/圆形/自定义截面的创建,以及变截面组 TaperEle。截面方案由桥型层决定,API 参数细节不在本 SKILL 范围。
---

# osis-module-section

> 截面模块。负责把桥型层决定的截面方案转为截面对象,供下游单元引用。

## 接到任务后,按顺序做

1. **从桥型层读取截面方案**(截面类型、梁高、桥宽、室数、变截面控制点)。
2. **选截面 API**。参数化 `create_<类型>` 优先;只有参数化 API 无法表达时才用 `create_custom`。有哪些类型、各自参数用 `api_grep` / `api_read` 查(如 `api_grep "def create_" section`)。
3. **生成截面对象**(每个截面单独创建)。
4. **设置偏移与网格**(`set_offset` / `set_mesh`)。
5. **把截面编号、名称、用途写入建模状态**。
6. **若涉及变截面**,创建变截面组。

> 不在此模块决定节段长度、节点 x 坐标、钢束布置 —— 那些由对应模块负责。

## 创建截面的硬规则

- **显式传 `no`(第一个位置参数),不要传 `None`**。自动分配会让下游 `_6` 引用错乱,也无法同号覆盖重跑。
- **参数化截面**:从目标尺寸反推全部几何参数,不要只改 `h`/`bt`。详见 `references/section_transform.md` §参数化缩放。
- **自定义截面**:逐点变换 `contour_matrix`,全 z 等比缩放是错误做法(板厚、倒角会变形)。详见 `references/section_transform.md` §自定义变换。

## 坐标系约定

```
Y=0 ───────── 截面横向中心(Middle)
Z=0 ───────── 顶面
Z 负方向 ──── 向下
```

所有 `create_*` 的 y、z 参数遵循此约定。

## 偏移与网格

每个截面创建后必须设置:

```python
sec.set_offset(
    offset_type_y="Middle",    # "Left"/"Middle"/"Right"/"Manual"
    offset_value_y=0.0,
    offset_type_z="Center",     # "Top"/"Center"/"Bottom"/"Manual"
    offset_value_z=0.0,
)
sec.set_mesh(mesh_method=0, mesh_size=0.1)   # 0=默认, 1=自定义
```

- **`offset_type_z` 默认是 `"Center"`,不是 `"Top"`**;主梁顶缘对齐要显式传 `"Top"`。
- **`set_mesh` 的参数名是 `mesh_method`,不是 `method`**。
- **偏移**:中梁/边梁 y 偏移由截面 API 的梁位参数决定(各 API 名字不同,如 `e_girder_pos` / `girder_pos`,取值大小写也不同,以 `api_read` 为准),`offset_value_y` 通常为 0。自定义截面的 y 偏移需显式给出。
- **网格**:默认 0.1m;变截面段可加密到 0.05m,桥墩等粗略截面可用 0.2m。

## 变截面组(TaperEle)

在两端截面之间由 OSIS 自动生成中间截面序列,不用手建大量中间截面。**仅当**以下条件都满足时用:

- 参数化截面:L 型/倒 L 型、T 型/倒 T 型、工字型、圆/圆管形、实心/空腹矩形(可倒圆/斜角)、实心/空腹圆端形、小箱梁、T 梁、常规箱梁。**不支持** `create_custom`
- 整组单元的 `sec1`/`sec2`、`z_trans`、`y_trans` 一致(变截段统一用浅→深或深→浅)

```python
engine.element.taper_group.create(
    "变截面-左", 1, 2.0, 0, 0.0,   # name, z_type(0 线性/1 多项式), z_trans(多项式指数), z_pos(0=I 端/1=J 端), z_dis
    0, 1.0, 0, 0.0,                # y_type, y_trans, y_pos, y_dis
    "3to18",                       # *eles:单号 varargs 或 "5to10" 区间
)
```

- `*eles` 是 varargs,**关键字参数后不能再跟位置参数**——前 9 个参数全位置传。
- 组只覆盖变截段,不含两侧等截面段。
- 同名重复创建是**覆盖语义**,重跑不报错。
- 生成的中间截面命名如 `408_组1_408`;导出命令流时 TaperEle 被注释,用这些独立截面替代。
- 只需单个单元内部变高时,用 `create_beam3d(..., z_trans=2)` 即可,不必建组。

**抛物线凹向**由 `z_pos` 决定(该端斜率为 0):`z_pos` 在深端一侧 → 梁底朝下鼓;在浅端一侧 → 梁底朝上凹。例:浅→深段 `z_pos=0`、深→浅段 `z_pos=1` 都是浅端贴平、梁底朝上凹(墩顶加深的连续梁常用)。

## 失败模式

- **`该参数组合几何检查不通过`** —— 改 `h` 后未联动改 `tb`/`tw`/`bb`。从目标 h 反推全部几何参数
- **截面 API 梁位参数与 `set_offset` 重复设 y 偏移** —— 只在一处设
- **TaperEle 用在自定义截面** —— 不支持,改用参数化 API

(其他见 `osis-engine/references/error_diagnosis.md`)
