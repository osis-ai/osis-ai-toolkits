---
name: osis-module-tendon
description: 预应力钢束建模模块。生成钢束规格(prop)、线型曲线(shape 之前的 2d/3d arc)、钢束形状(shape + layout)、施加预应力 4 步流程。处理控制点 x 与 element_group 范围一致约束、张拉与构件激活阶段匹配、贴底束 bottom() 贴底机制与出梁排查顺序。**具体钢束命名清单、规格、张拉参数由桥型层 SKILL 决定**。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-tendon

> 钢束模块。把桥型层决定的钢束体系转为可施加的预应力对象。

## 接到任务后,按顺序做

**严格按 4 步顺序**,不可跳步、不可重排:

1. **创建钢束规格**(`tendon.prop.create`)
2. **创建线型曲线**(`geometry.create_arc2d` / `geometry.create_arc3d`)
3. **创建钢束形状**(`tendon.shape.create_arc2d` / `tendon.shape.create_arc3d` + `tendon.shape.layout`)
4. **绑定到荷载工况**(`load.<lc>.create_prestress`)—— 由 `osis-module-loadcase` 在其模块内完成

> 第 4 步实质属于 loadcase 模块。本 SKILL 负责 1~3 步;第 4 步由 `osis-module-loadcase` 调 `create_prestress` 绑定,需引用本模块的 shape 名。

## 钢束规格 `tendon.prop`

体内后张按规范:`tendon.prop.create_in`,或 `create(..., s_type="IN", area=1)`。完整签名见 `references/prop_create.md`。

默认值:`diameter=15.2`、`pipe=0.09`、`friction_coeff=0.17`、`deviation_coeff=0.0015`、`starting_deform=0.006`、`end_deform=0.006`、`tensioning_coeff=1.0`、`relaxation_coeff=0.30`、`code="GBT5224_2014"`。`mat` 用 `_3` 钢绞线材料号;规格名常用 `'15-N'`。

## 线型曲线(锚固点 + 转折点)

钢束在 2D/3D 空间的控制点序列,通过 `engine.geometry` 创建。

通用入口 `geometry.create(name, type, *coords)` 按 `type`(`"GENERAL"`/`"NATURAL"`/`"ARC2D"`/`"ARC3D"`)路由到 `create_general`/`create_natural`/`create_arc2d`/`create_arc3d`,关系同其他模块:只多一个 `type` 路由参数,其余参数(`owner` 标志 + 坐标 varargs)与对应 `create_*` 完全一致。

### 2D 圆弧(竖向平面,跨径方向 + 高度)

```python
geometry.create_arc2d(
    name,                    # 曲线名
    "TENDON",                # owner 标志("TENDON"=钢束)
    x1, y1, r1,              # 4~6 个控制点(每个点: x, y, r)
    x2, y2, r2,
    x3, y3, r3,
    x4, y4, r4,
)
```

**位置参数是 varargs**,不是 list。`r` 为该点曲率半径(`0` = 直线/锚固端)。

### 3D 圆弧(空间曲线)

```python
geometry.create_arc3d(
    name,
    "TENDON",
    x1, y1, z1, r1,
    x2, y2, z2, r2,
    ...
)
```

| 参数 | 含义 |
|---|---|
| `(x, y)` 或 `(x, y, z)` | 控制点坐标 |
| `r` | 该点曲率半径(0 = 直线/锚固端) |

**典型 4 点 ARC3D**:首尾 `r=0`(锚固),中部 `r=10~75`(曲线段)。**不要 6 点**——容易出现夹角 > 90° 导致 `夹角大于90度` 错误。

## 钢束形状 `tendon.shape`(绑定到单元组)

`shape.create_*` 返回 `TendonShape` **handle 对象**;`layout()` 是在 handle 上调,不在 manager 上调。

通用入口 `tendon.shape.create(name, n_num, prop, element_group, layout_type, ...)` 按 `layout_type`(`"SPL3D"`/`"ARC3D"`/`"ARC2D"`)路由到 `create_spl3d`/`create_arc3d`/`create_arc2d`,关系同 `prop.create`:只多一个路由参数,其余参数完全一致。

### 3D 圆弧

```python
shape = engine.tendon.shape.create_arc3d(
    name,                          # 钢束形状名
    n_num=2,                       # 钢束根数
    prop="15-15",                  # 用哪个 prop
    element_group="BB4-yGp",       # 钢束投影组(必须已在 `_6` 建好)
    curve_name="BB4-y_VerCurve",   # 上一步的曲线名
)
shape.layout("GLOBAL")            # 或 layout("ELEMENT", ...)
```

### 2D 圆弧

```python
shape = engine.tendon.shape.create_arc2d(
    name,
    n_num=2,
    prop="15-15",
    element_group="BB4-yGp",
    e_type=1,                      # 0=距离参考 / 1=坐标参考
    # 接下来是 2 个或 4 个控制点(根据 e_type)
    "BB4-y_VerCurve",              # 竖弯样条曲线名
    "BB4-y_HorCurve",              # 平弯样条曲线名
)
```

`element_group` **必须等于** `osis-module-element` 的 `element.group.create('BB4-yGp', 'c')` 创建的组名。否则报"组不存在"。

> **幂等性(实测)**:`tendon.prop.create*` 同名重复创建是**覆盖语义**,重跑不报错;但 `tendon.shape.create*` **不是幂等的**——同名形状已存在时报"创建钢束形状失败"。单模块重跑 `_8` 前先删同名形状:
> ```python
> if engine.tendon.shape.get(name):
>     engine.run(f"TdShapeDel,{name}")   # shape.delete() 依赖 GetReferences 接口,部分 OSIS 版本不通,用原始命令更稳
> shape = engine.tendon.shape.create_arc3d(name, ...)
> ```
> 线型曲线(`geometry.create_*`)同名重复创建也是覆盖语义。详见 `osis-engine/references/incremental_rerun.md`。

## layout 模式

```python
shape.layout(layout_type, n_ele=..., n_beg=..., n_dir=..., d_offset_x=..., d_offset_y=..., d_offset_z=...)
```

| `layout_type` | 含义 | 何时用 |
|---|---|---|
| `'GLOBAL'` | 全局坐标定位 | 钢束曲线是空间 3D,按全局 x/y/z |
| `'ELEMENT'` | 按单元局部坐标定位 | 钢束曲线依附单元(如端横梁局部束) |

`'ELEMENT'` 模式需要额外参数 `n_ele`(参考单元编号)、`n_beg`(0=i / 1=j)、`n_dir`(0=i→j / 1=j→i)及三向偏移。

`'GLOBAL'` 模式会校验钢束 x 范围是否落在 `element_group` 范围内。不一致时报"形状控制点坐标超出参照单元组的坐标范围"。

## 贴底束 `bottom()` 机制(通用)

`shape.bottom(b_bot, *bot)`(底层命令 `BottomTS`)把竖曲线指定行标记为沿梁底自动布置:

```python
shape = engine.tendon.shape.create_arc2d("BB5-z", 2, "15-19", "BB5-zGp", 1, "BB5-z_VerCurve", "BB5-z_HorCurve")
shape.layout("ELEMENT", 1, 0, 0, 0.0, 0.0, 0.0)
shape.bottom(1, 2, 3)        # 竖曲线第 2、3 行沿梁底自动布置
```

**语义(2026-07-31 开关对照实验实锤:`bottom(0)` 钢束立即按字面 z 出梁,恢复 `bottom(1, 2, 3)` 即回贴底)**:

- **被标记行**由 OSIS 按梁底自动布置,曲线里这些行的 z 是占位值,不参与定位
- **未标记行**(锚端行)z 按字面生效
- 适用范围:贴底束(底板束 BB/ZB 类;具体哪些束挂 bottom 由桥型层指定)。预制束、直线束不用

**BottomTS 设置挂在模型的形状对象上,不在曲线/文件里**:`_8` 完整重跑(create→layout→bottom)会重挂;但重跑中途失败、手工删建 shape 之后,文件里有 `.bottom()` ≠ 模型里有(7-30 实测:文件完好但模型未应用,字面 z 出梁 0.67m,抬 z 只是压住表象)。

**钢束出梁排查顺序(铁律):先看模型里 bottom 是否挂上(目视,或 `bottom(0)` / `bottom(1, ...)` 开关对照),再查行结构,最后才动 z。**

修改贴底束曲线时:

- **保行数、行序和 bottom 行号**——删行会让 bottom 行号错位并拉长直弦(实测 4 行删成 3 行,弦中点下垂出梁 0.11m)
- **贴底行只动 x、不改 z**(z 由 OSIS 按梁底布置,改了也不参与定位)
- **锚端行 z 保持距梁底原高度**,并按新 x 处梁高核净空 ≥0.11m
- 典型 4 行竖曲线:锚端(字面 z)→ 快速下弯行(bottom 行)→ 贴底终点(bottom 行)→ 上弯锚端(字面 z);具体行数以桥型模板为准

## 钢束命名体系(按位置)

命名按**位置 + 偏置 + y/z** 约定,让下游按名引用不出错:

| 前缀 | 含义 | 命名样例 |
|---|---|---|
| `BB` | 底板束(Bottom Bar) | `BB4-y` / `BB4-z`(y/z 偏置) |
| `BT` | 边跨顶板束(Beam Top) | `BT3-y` / `BT3-z` |
| `F` | 跨中腹板束(F-loop) | `F0-1` / `F8-2`(节段 + 编号) |
| `T` | 跨中顶板束(Top) | `T0-1` / `T8-2` |
| `ZB` | 中跨底板束(Zhong Bottom) | `ZB3-1` / `ZB8-1` |
| `ZT` | 中跨顶板束(Zhong Top) | `ZT3-1` / `ZT7-1` |

数字部分(节段号)对应 `_6` 元素的节段分组。**组名要逐字一致**。

## 钢束命名(由桥型层决定)

具体钢束命名清单(底板束/顶板束/腹板束等各类有多少条、叫什么)由**桥型层 SKILL 决定**。本模块负责:

- 按桥型层给的命名清单生成钢束
- 保持命名风格统一(位置 + 偏置,如 `xxx-y` / `xxx-z`;或节段 + 编号,如 `xxx-1` / `xxx-2`)

**组名逐字一致**。建好后写入状态,下游按名引用。

## 张拉参数(在 `loadcase` 模块的 `create_prestress` 中)

第 4 步 `create_prestress` 的关键参数:

| 参数 | 取值 | 含义 |
|---|---|---|
| `tension_type` | `"BOTH"` / `"BEG"` / `"END"` | 张拉方式(两端/起点/终点) |
| `tension_force_type` | `"ST"` / `"IF"` | 控制方式(应力/内力) |
| `beg` / `end` | Pa(注意单位!) | 张拉控制力 |

**张拉方式与控制应力由桥型层给定**。本模块不规定具体数值。

## 改跨径时怎么改钢束

**悬浇三跨先跑 `osis-engine/scripts/spanremap.py`**,不要手改 `_2` 数字。本节留给脚本失败后的补丁,以及刚构/预制。

近邻模板只提供**骨架**(束名、4 点模式、规格、投影组名、`bottom` 行号)。钢束控制点是**绝对坐标**,不是跨径比例;改跨径时要在已解曲线上按区平移/拉伸 x,保持点数、半径和贴底行结构。按新梁高重新拟合一整套点会丢掉这些已解几何,容易穿梁、急折、夹角>90。

### 改哪个 `.py`

| 文件 | 内容 | 改跨径时 |
|---|---|---|
| `_2_property.py` | `geometry.create(曲线名, "ARC2D"/"ARC3D", "TENDON", x,y,z,r, ...)` | 在**已有行**上改坐标数字;名字、点数、`r` 不动 |
| `_6_element.py` | 投影组(如 `F1-2_CurveGp`)含哪些单元号 | 单元编号未变则不动;变了按新节点 x 重选,使组覆盖该曲线 x |
| `_8_loadcase.py` | prop、`shape.create`(只引用曲线名和组名)、layout、bottom、PST | 名字没变就不动 |

命令流最后一条 `LayoutTS,<shape名>` / `TdShape,<shape名>` 就是要改的对象:在 `_2` 搜同名 `_Curve` / `_VerCurve`,改那一行的 x。`*-z` 锚左梁端,`*-y` 锚右梁端,两侧不要写成同一段 x。

写回:曲线同名覆盖,可 L1 `_2`;shape 非幂等,模型里已有该 shape 时先 `TdShapeDel` 再 L1 `_8`,或一次 L2。

### 控制点怎么动

1. **先看节段方案是否同构**(每 T 构节段对数、合龙段 2m、0 号块分段是否一样)。同构才能走桥型层「只改 `_5` x + `_2` 曲线 x,`_6`~`_10` 零改动」。节段对数不同(如 13 对 vs 16 对)→ **换一座同节段方案的近邻**。
2. **x 按区动,不要整桥比例缩放**:
   - **平移区**(过了模板墩位的点):统一 `+Δx`(新墩位 − 旧墩位),半径/过渡段不动
   - **拉伸区**(边跨现浇/边跨合龙内的点):锚固端保持距梁端 0.15~0.20m,中间点跟所在节段新端点走
   - 中跨变长/变短由**跨中恒高直线段**吸收,曲线段(起弯点、半径)不缩放
3. **贴底束(BB/ZB)**:保 4 行 + `bottom` 行号;贴底行只改 x 不改 z;锚端 z 按新 x 处梁高核净空 ≥0.11m
4. **投影组**覆盖的节点 x 必须盖住新曲线 x
5. **验收**:侧立面绿线在梁内、无急折/穿出;无 `LayoutTS`/`夹角大于90度`/`控制点超出参照单元组`

悬浇三跨走 `spanremap`;刚构见该桥型「跨中直线段截短、曲线段不变」。

## 钢束张拉与构件激活阶段匹配

**钢束张拉阶段必须晚于钢束对应构件的激活阶段**。具体张拉阶段编号由桥型层 SKILL 在阶段序列中给定。

**不允许**钢束张拉在构件激活之前,否则 `shape.layout('GLOBAL')` 报错"钢束进入未激活单元"。

## 报告状态

→ `osis-engine` §维护建模状态 表,本 module 写 `tendons` 字段(钢束规格、形状、投影组对应、锚固曲线、张拉参数、张拉阶段)。

**钢束 shape 名与预应力工况名是两个名字空间**:shape 名(如 `N1-1`)只给 `_8` 的 `create_prestress`/`create("PST", ...)` 的 `entity` 用;工况名(如 `预应力腹板束`)由 `osis-module-loadcase` 创建、给 `_10` 的 `define_loadcase` 用。`_10` 永远不引用 shape 名。

## 失败模式

- **`夹角大于90度`** —— 钢束控制点排布使弧线出现折返。用 4 点 ARC3D,不要 6 点;首尾 r=0,中部 r=10~75
- **`形状控制点坐标超出参照单元组的坐标范围`** —— 钢束曲线 x 范围超出了 element_group 覆盖。同步缩钢束端点与 element_group
- **`shape.layout('GLOBAL')` 报错 / 预应力工况需张拉/钝化的预应力所在的单元尚未激活** —— 同步缩钢束端点到当前阶段激活的单元范围
- **张拉控制应力单位错** —— 应该是 Pa(1.395e9),不是 MPa(1395)
- **钢束组名引用不一致** —— `element_group` 不在 `_6` 建好,或名称差一个字符
- **钢束 z 低于梁底、脱出混凝土** —— 第一嫌疑是 bottom 没挂上(BottomTS 挂模型形状对象、不挂文件);按 §贴底束 bottom() 机制 的排查顺序:bottom → 行结构 → z,别急着抬 z
- **改跨后绿线穿梁/急折** —— 梁的节点 x 改了,钢束曲线仍停在旧绝对坐标,或按新梁高重拟合了控制点、丢掉了 4 点/半径/贴底行。按 §改跨径时怎么改钢束 做区平移,不要整桥缩放

(其他见 `osis-engine/references/error_diagnosis.md`)

## 协作

| 上下游 | 交接 |
|---|---|
| 桥型层 → 本模块 | 钢束体系命名表(数量、命名、规格、张拉参数) |
| 上游 `osis-module-material` | 钢绞线材料号(`mat`) |
| 上游 `osis-module-element` | 钢束投影组(`element_group` 名称) |
| 上游 `osis-module-node` | 锚固点 x(钢束曲线端点 x 与已建节点对齐) |
| 下游 `osis-module-loadcase` | 钢束 shape 名(`create_prestress` 引用) |
| 下游 `osis-module-stage` | 钢束张拉阶段号 |
