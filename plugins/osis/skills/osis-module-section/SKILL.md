---
name: osis-module-section
description: 截面建模模块。生成 `prep/_4_section.py`,负责创建截面、设置偏移与网格、决定截面编号供下游单元引用。处理箱梁/矩形/圆形/自定义截面的创建,以及变截面组 TaperEle。截面方案由桥型层决定,API 参数细节不在本 SKILL 范围。
---

# osis-module-section

> 截面模块。负责把桥型层决定的截面方案转为截面对象,供下游单元引用。

## 接到任务后,按顺序做

1. **从桥型层读取截面方案**(截面类型、梁高、桥宽、室数、变截面控制点)。
2. **选截面 API**。参数化 API 优先;只有参数化 API 无法表达时才用 `create_custom`。
3. **生成截面对象**(每个截面单独创建,显式指定 `no` 编号,保证幂等)。
4. **设置偏移与网格**(`set_offset` / `set_mesh`)。
5. **把截面编号、名称、用途写入建模状态**(`sections` 字段)。
6. **若涉及变截面**,创建变截面组。

> 不在此模块决定节段长度、节点 x 坐标、钢束布置 —— 那些由对应模块负责。

## 公共约定

`section.create_*` 系列方法,**第一个位置参数都是 `no`(截面编号)**,第二个是 `name`,然后是各类型专属参数。`no` 显式传可保证幂等。

`section.create(no, name, type, *args, **kwargs)` 是通用入口,按 `type` 字符串派发到具体 `create_*` 方法。`type` 可选值见下方表格。

## 选截面 API

按桥型 + 截面形式选择:

| `type` | 派发到 | 用途 |
|---|---|---|
| `"CONVENTIONALBOX"` | `create_conventionalbox` | 常规箱梁(单/多室) |
| `"STREAMEDBOX"` | `create_streamed_box` | 扁平箱梁 |
| `"DOUBLESIDEBOX"` | `create_double_side_box` | 双边箱梁 |
| `"SMALLBOX"` | `create_smallbox` | 小箱梁 |
| `"TGIRDER"` | `create_TGirder` | T 梁 |
| `"HOLLOWSLAB"` | `create_hollowslab` | 空心板 |
| `"RECT"` | `create_rect` | 矩形(桥墩等) |
| `"CIRCLE"` | `create_circle` | 圆形 |
| `"LSHAPE"` / `"TSHAPE"` / `"ISHAPE"` | `create_Lshape` / `create_Tshape` / `create_Ishape` | L/T/I 形 |
| `"ROUNDEDEND"` | `create_rounded_end` | 圆端形 |
| `"RIBBEDSLAB"` | `create_ribbed_slab` | 肋板式 |
| `"CUSTOM"` | `create_custom` | 通用自定义(用 `contour_matrix`) |
| `"STEELI"` / `"STEELBOX"` / ... | 钢梁系列 | 钢结构 |
| `"COMPOSITESTEELI"` / ... | 钢-混组合系列 | 组合结构 |
| `"NUMERICAL"` | `create_numerical` | 数值截面(直接给面积/惯性矩) |

每个 `create_*` 的具体参数见 `references/section_transform.md`,此处不列全(参数多,API 参考 pyosis 源码)。

**`create_*` 与 `create()` 的关系**:两者只差一个 `type` 路由参数,其余参数(顺序、含义、默认值)完全一致——`create_*` 等价于 `create()` 帮你填好了 `type`。例:`create(1, "跨中", "CIRCLE", "Solid", 0.5, 0.02)` ≡ `create_circle(1, "跨中", "Solid", 0.5, 0.02)`。日常推荐 `create_*`;`create()` 适合按配置表/循环动态派发。

## 创建截面的硬规则

- **显式传 `no=`**。保证幂等,重跑模块不冲突。
- **不传 `no` 用 None**。OSIS 自动分配编号会让下游 `_6` 引用错乱。
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
    offset_type_z="Center",     # "Top"/"Center"/"Bottom"/"Manual"(默认 "Center",不是 "Top")
    offset_value_z=0.0,
)

sec.set_mesh(
    mesh_method=0,             # 0=默认, 1=自定义
    mesh_size=0.1,             # 网格尺寸(m)
)
```

- **`offset_type_z` 默认是 `"Center"`,不是 `"Top"`**。
- **`set_mesh` 的参数名是 `mesh_method`,不是 `method`**。
- **偏移**:中梁/边梁 y 偏移由 `e_girder_pos` 决定,`offset_value_y` 通常为 0(由 API 内部处理)。自定义截面的 y 偏移需显式给出。
- **网格**:0.1m 是常用值,关键截面(变截面段)可用 0.05m 加密,粗略截面(桥墩)可用 0.2m。

## 变截面组(TaperEle)

**仅当** 9 种参数化截面类型之一 且 整组单元两端截面一致 时使用。详见 `references/taper_group.md`。

```python
tg = engine.element.taper_group.create(
    name, 0, 1.0, 0, 0.0,       # z_type=0(线性), z_trans=1.0, z_pos=0(i端), z_dis=0.0
    0, 1.0, 0, 0.0,             # y_type=0(线性), y_trans=1.0, y_pos=0, y_dis=0.0
    1, 2, 3, 4, 5,              # *eles 单元编号 varargs(支持 "5to10" 区间)
)
```

> **签名**:`create(name, z_type, z_trans=1.0, z_pos=0, z_dis=0.0, y_type=0, y_trans=1.0, y_pos=0, y_dis=0.0, *eles)`。
> `*eles` 是 varargs,**关键字参数后不能再跟位置参数**(Python 语法错误)——前 9 个参数要么全位置传,要么全关键字传,`*eles` 永远位置传。同名重复创建是**覆盖语义**(生成或修改),重跑不报错。

TaperEle 工作流:

1. 创建两端截面(深/浅)
2. 单元赋予相同 `n_sec1`/`n_sec2`(变截段统一用浅→深或深→浅)
3. 调用 `engine.element.taper_group.create(...)` 注册
4. OSIS 自动生成中间截面,命名如 `408_组1_408`

**不允许**对自定义截面用 TaperEle。

## 报告状态

→ `osis-engine` §维护建模状态 表,本 module 写 `sections` 字段(截面编号、名称、类型、用途、变截面控制点)。

## 失败模式

- **`该参数组合几何检查不通过`** —— 改 `h` 后未联动改 `tb`/`tw`/`bb`。从目标 h 反推全部几何参数,不要只改 `h`
- **`set_offset` 与 `e_girder_pos` 冲突** —— 不要同时在 API 和 `set_offset` 里设置 y 偏移
- **TaperEle 用在自定义截面** —— 不支持,改用参数化 API

(其他见 `osis-engine/references/error_diagnosis.md`)

## 协作

| 上下游 | 交接 |
|---|---|
| 桥型层 → 本模块 | 截面方案(类型、尺寸、变截面控制点、节段数) |
| 本模块 → `osis-module-element` | 截面编号、名称(单元引用 `n_sec1`/`n_sec2`) |
| 本模块 → `osis-module-rebar`(可选) | 截面编号(钢筋按截面布置) |
| 本模块 → `osis-module-tendon`(可选) | 截面边界(钢束 z 受顶/底板约束) |
