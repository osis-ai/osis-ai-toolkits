---
name: osis-module-tendon
description: 预应力钢束建模模块。生成钢束规格(prop)、线型曲线(shape 之前的 2d/3d arc)、钢束形状(shape + layout)、施加预应力 4 步流程。处理控制点 x 与 element_group 范围一致约束、张拉与构件激活阶段匹配、贴底束 bottom() 贴底机制与出梁排查顺序。**具体钢束命名清单、规格、张拉参数由桥型层 SKILL 决定**。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-tendon

> 钢束模块。把桥型层决定的钢束体系转为可施加的预应力对象。

## 接到任务后,按顺序做

**严格按 4 步顺序**,不可跳步、不可重排:

1. **创建钢束规格**(`tendon.prop.create_in` 等,写在 `_8`)
2. **创建线型曲线**(`geometry.create_arc2d` / `create_arc3d`,写在 `_2_property.py`)
3. **创建钢束形状**(`tendon.shape.create_*` + `layout`,写在 `_8`)
4. **绑定到荷载工况**(`lc.create_prestress`)—— 由 `osis-module-loadcase` 完成,引用本模块的 shape 名

## 钢束规格 `tendon.prop`

```python
engine.tendon.prop.create_in(
    name="15-15", mat=5, code="GBT5224_2014", diameter=15.2, num=15, pipe=0.09,
    friction_coeff=0.17, deviation_coeff=0.0015,
    starting_deform=0.006, end_deform=0.006,
    tensioning_coeff=1.0, relaxation_coeff=0.30,
)
```

| 参数 | 含义 |
|---|---|
| `name` | 规格名,常用 `'15-N'`(N=每束根数) |
| `mat` | `_3` 钢绞线材料号 |
| `code` | `GBT5224_2014` 或 `GBT20065_2016` |
| `diameter` / `num` / `pipe` | 单股直径(mm)/ 每束钢绞线根数 / 管道直径(m) |
| `friction_coeff` / `deviation_coeff` | 摩擦系数 / 偏差系数 |
| `starting_deform` / `end_deform` | 锚具回缩(m) |
| `tensioning_coeff` / `relaxation_coeff` | 张拉系数 / 松弛系数 |

- **摩阻、偏差、回缩、张拉、松弛系数必须显式传**:API 默认值是 1.0 / 0.0 这类占位值,不是工程值。项目没给时用上面示例的值。
- 通用入口 `prop.create(name, s_type, mat, area, ...)` 多两个路由参数:`s_type`(`"IN"` 体内 / `"EX"` 体外 / `"PRE"` 先张)、`area`(`1` 按规范 / `0` 输入面积),其余同 `create_in`。

## 线型曲线

```python
engine.geometry.create_arc3d("N1-1_Curve", "TENDON", [x1, y1, z1, r1, x2, y2, z2, r2, ...])   # 每点 x, y, z, R
engine.geometry.create_arc2d("BB4-y_VerCurve", "TENDON", [x1, y1, r1, x2, y2, r2, ...])        # 每点 x, y, R
```

- 坐标是**一个 list**,按点平铺。
- `R` 是该点圆弧半径,锚固端和直线点为 0。
- 同名重复创建是覆盖语义。

## 钢束形状 `tendon.shape`

```python
shape = engine.tendon.shape.create_arc3d("N1-1", 2, "15-15", "N1-1_CurveGp", "N1-1_Curve")   # name, n_num, prop, element_group, curve_name
shape.layout("GLOBAL")

shape = engine.tendon.shape.create_arc2d("BB4-y", 2, "15-19", "BB4-yGp", 1, "BB4-y_VerCurve", "BB4-y_HorCurve")
#                                                                       e_type=1(坐标参考)后接 竖弯曲线名, 平弯曲线名
shape.layout("ELEMENT", 1, 0, 0, 0.0, 0.0, 0.0)
```

- `create_*` 返回 `TendonShape` 对象,`layout` / `bottom` 在对象上调。
- `create_arc2d` 的 `e_type` 后面跟的是位置参数,`e_type` 也要位置传(关键字参数后不能再跟位置参数)。`e_type=0`(距离参考)时参数是:竖弯参考位置、竖弯曲线名、平弯参考位置、平弯曲线名。
- `element_group` 必须等于 `_6` 建好的投影组名。
- **shape 不幂等**:同名已存在报"创建钢束形状失败"。重跑前删同名形状(`shape.delete()` 依赖 `GetReferences`,部分 OSIS 版本不通,用原始命令):

```python
if engine.tendon.shape.get(name):
    engine.run(f"TdShapeDel,{name}")
```

### layout

| `layout_type` | 含义 | 何时用 |
|---|---|---|
| `"GLOBAL"` | 参考整体坐标系 | 曲线按全局 x/y/z 给出 |
| `"ELEMENT"` | 参考单元局部坐标 | 曲线依附某单元;另传 `element`(参考单元号)、`begin`(0=i / 1=j)、`direction`、三向偏移 |

`GLOBAL` 会校验钢束 x 范围是否落在 `element_group` 内,超出报"形状控制点坐标超出参照单元组的坐标范围"。

## 贴底束 `bottom()` 机制

`shape.bottom(1, *行号)`(底层命令 `BottomTS`)把竖曲线指定行标记为沿梁底自动布置:

```python
shape.bottom(1, 2, 3)        # 竖曲线第 2、3 行沿梁底自动布置
```

- **被标记行**由 OSIS 按梁底布置,曲线里这些行的 z 是占位值,不参与定位;**未标记行**(锚端行)z 按字面生效。`bottom(0)` 关掉后钢束立即按字面 z 走。
- 适用:贴底束(哪些束挂 bottom 由桥型层指定)。预制束、直线束不用。
- **BottomTS 挂在模型的形状对象上,不在曲线/文件里**:`_8` 完整跑一遍(create → layout → bottom)会重挂;但中途失败或手工删建 shape 后,文件里有 `.bottom()` 不等于模型里有,钢束会按字面 z 出梁。

**钢束出梁排查顺序:先看模型里 bottom 是否挂上(目视,或 `bottom(0)` / `bottom(1, ...)` 开关对照),再查行结构,最后才动 z。**

修改贴底束曲线时:

- **保行数、行序和 bottom 行号**——删行会让 bottom 行号错位并拉长直弦,弦中点下垂出梁
- **贴底行只动 x、不改 z**
- **锚端行 z 保持距梁底原高度**,按新 x 处梁高核净空
- 常见 4 行结构:锚端(字面 z)→ 快速下弯(bottom 行)→ 贴底终点(bottom 行)→ 上弯锚端(字面 z);以现有曲线的行结构为准

## 命名

钢束命名清单(各类束多少条、叫什么、投影组名)由**桥型层 SKILL 决定**。本模块按清单生成,建好后写入状态;投影组名与 `_6` 逐字一致。

**shape 名与预应力工况名是两个名字空间**:shape 名(如 `N1-1`)只用于 `create_prestress` 的 `entity`;工况名(如 `预应力腹板束`)由 `osis-module-loadcase` 创建、给 `_10` 的 `define_loadcase` 用。`_10` 永远不引用 shape 名。

张拉方式、控制应力由桥型层给定,写法见 `osis-module-loadcase` §预应力绑定。

## 改跨径时怎么改钢束

桥型 SKILL 有专用流程(如悬浇三跨的 `spanremap` 脚本)时先走它。本节是通用做法。

复制来的钢束曲线是已解几何:束名、点数、半径、规格、投影组名、`bottom` 行号都已对。控制点是**绝对坐标**,不是跨径比例。改跨径时在已有曲线上按区平移/拉伸 x,保持点数、半径和贴底行结构;按新梁高重新拟合一整套点会丢掉这些几何,容易穿梁、急折、夹角 > 90°。

### 改哪个 `.py`

| 文件 | 内容 | 改跨径时 |
|---|---|---|
| `_2_property.py` | `geometry.create_arc*(曲线名, "TENDON", [...])` | 在**已有行**上改坐标数字;名字、点数、`R` 不动 |
| `_6_element.py` | 投影组含哪些单元号 | 单元编号未变则不动;变了按新节点 x 重选,使组覆盖该曲线 x |
| `_8_loadcase.py` | prop、`shape.create`、layout、bottom、PST | 名字没变就不动 |

命令流最后一条 `LayoutTS,<shape名>` / `TdShape,<shape名>` 就是要改的对象:在 `_2` 搜同名曲线,改那一行的 x。

写回:只改了 `_2` 可单跑 `_2`(曲线同名覆盖);动了 `_6`/`_8` 或拿不准时跑 `main.py`(见 `osis-engine` §写回)。

### 控制点怎么动

1. **先确认节段/分段方案同构**。不同构(如节段对数不同)就换一个同构的近邻,不要硬改。
2. **x 按区动,不要整桥比例缩放**:
   - **平移区**(墩位以外整体移动的点):统一 `+Δx`(新墩位 − 旧墩位),半径/过渡段不动
   - **拉伸区**:锚固端保持原距梁端距离,中间点跟所在节段新端点走
   - 跨长变化由**跨中直线段**吸收,曲线段(起弯点、半径)不缩放
3. **贴底束**:按 §贴底束 的规则改。
4. **投影组**覆盖的节点 x 必须盖住新曲线 x。
5. **验收**:侧立面钢束在梁内、无急折/穿出;无 `LayoutTS` / `夹角大于90度` / `控制点超出参照单元组` 报错。

## 张拉与构件激活

**钢束张拉阶段必须晚于对应构件的激活阶段**,否则 `layout` 报"钢束进入未激活单元"。张拉阶段由桥型层在阶段序列中给定。

## 失败模式

- **`夹角大于90度`** —— 相邻控制点连线折返(点太密或半径太大)。回到原曲线结构,只按区移 x
- **`形状控制点坐标超出参照单元组的坐标范围`** —— 曲线 x 超出 `element_group` 覆盖。同步缩钢束端点或扩组
- **`预应力工况需张拉/钝化的预应力所在的单元尚未激活`** —— 钢束跨入当前阶段未激活的单元;缩端点或调张拉阶段
- **张拉控制应力单位错** —— 应为 Pa(1.395e9),不是 MPa
- **钢束组名引用不一致** —— `element_group` 没在 `_6` 建,或差字符
- **摩阻损失异常大** —— `create_in` 没显式传摩阻/偏差系数,用了 API 默认 1.0
- **钢束 z 低于梁底、脱出混凝土** —— 先查 bottom 是否挂上,按 §贴底束 的排查顺序:bottom → 行结构 → z
- **改跨后钢束穿梁/急折** —— 节点 x 改了而曲线仍停在旧坐标,或重拟合丢了点数/半径/贴底行。按 §改跨径时怎么改钢束 区平移

(其他见 `osis-engine/references/error_diagnosis.md`)
