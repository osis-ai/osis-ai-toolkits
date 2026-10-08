---
name: osis-module-loadcase
description: 荷载工况模块。生成 `prep/_8_loadcase.py`,创建工况(自重/二期/温度/线荷载/节点力),施加各类荷载。处理 load_case_type 速查表(CS/T/TG/USER/PS/SH/CR/...)、温度荷载的逐单元循环约束、预应力钢束的工况绑定。当总控按依赖顺序加载到本模块时使用。钢束的 prop/shape 仍由 `osis-module-tendon` 负责。
---

# osis-module-loadcase

> 荷载工况模块。决定有哪些工况、每种工况施加什么荷载。

## 接到任务后,按顺序做

1. **从 `profile` + 桥型层读取**:二期恒载值、温度模式、特殊荷载、是否含预应力。
2. **创建工况**(`load.create`),每工况显式指定 `name`,返回 `LoadCase` 对象。
3. **在 LoadCase 对象上调** `create_gravity` / `create_line_load` / `create_nforce` / `create_uniform_temperature` / `create_gradient_temperature` 施加荷载。
4. **预应力钢束**(如需)由 `osis-module-tendon` 提供 prop/shape,本模块在 LoadCase 上调 `create_prestress` 绑定到工况。
5. **把工况名、类型写入建模状态**(`loads` 字段)。

> 钢束的 prop/shape 创建属 `osis-module-tendon`;本模块只调用 `create_prestress` 把它绑到工况。

## 荷载工况类型速查(load_case_type)

| 类型 | 含义 | 类型 | 含义 | 类型 | 含义 |
|---|---|---|---|---|---|
| `USER` | 用户定义 | `PS` | 预加力 | `SH` | **收缩** |
| `CS` | 施工 | `EV` | 土的重量 | `CR` | **徐变** |
| `D` | 结构重力(恒载) | `EH` | 土侧压力 | `B` | 水浮力 |
| `T` | 均匀温度 | `TG` | 梯度温度 | `FR` | 支座摩阻力 |
| `L` | 汽车荷载 | `IF` | 汽车冲击力 | `CF` | 汽车离心力 |
| `W1` / `W2` | 活载风/极限风 | `SF` | **流水压力** | `LS` | 汽车引起的土侧压力 |
| `BRK` | 汽车制动力 | `CRL` | **人群荷载** | `FL` | **疲劳荷载** |
| `IP` | 冰压力 | `WF1` / `WF2` | W1/W2引起的波浪力 | `CFS` | **船舶的撞击作用** |
| `E` | 地震作用 | `CFD` | 漂流物的撞击作用 | `CFV` | **汽车撞击作用** |
| `STL` | 基础变位(不均匀沉降) | | | | |

> 以 `LoadCaseManager.create` 源码 docstring 为准:`SH`=收缩、`CR`=徐变(不要记反);沉降类用 `STL`,不是 `EV`。

> **二期/预应力/自重均为 `CS` 类型**。

```python
lc = engine.load.create("主梁自重", load_case_type="CS", scalar=1.0)
```

`create` 返回 `LoadCase` 对象;**所有 `create_*` 荷载都是在 LoadCase 对象上调,不是 manager**。

## 自重(CS)

```python
lc.create_gravity(x_coeff=0, y_coeff=0, z_coeff=-1.04)
```

- **参数名是 snake_case**(`x_coeff`/`y_coeff`/`z_coeff`),写成 camelCase(`dZCoeff=...`)会抛 `TypeError`
- 系数乘 g,**负=向下**;模板统一 `-1.04`(1.04 计入钢筋等超重)
- `x_coeff` / `y_coeff` 横/纵向分量,一般 0

## 二期恒载(线荷载)

```python
lc.create_line_load(
    entity=1,
    coord_system=0,            # 0=单元坐标系, 1=整体坐标系
    load_type=0,               # 0=连续, 1=离散
    offset_x_i=0.0, offset_x_j=1.0,    # 满布(0~1 覆盖全杆长)
    fz_i=-22000, fz_j=-22000,          # N/m(SI),负值向下
    # 其余参数按需
)
```

- **参数名是 snake_case**(`entity`/`coord_system`/`load_type`/`offset_x_i`/`fz_i`...),写成 camelCase(`nEntity=`/`dFZI=`)会抛 `TypeError`
- `load_type=0` 满布
- `offset_x_i=0, offset_x_j=1` 覆盖单元全长
- 多个单元用 for 循环逐个施加(不接受 `'1to10'` 字符串区间)

## 节点力

```python
lc.create_nforce(
    entity=node,
    fx=0, fy=0, fz=-28000,
    mx=0, my=0, mz=0,
)
# 模板常用便捷入口(与 _8 一致)
lc.create("NFORCE", node, 0.0, 0.0, -28000.0, 0.0, 0.0, 0.0)
```

- **参数名是 snake_case**(`entity`/`fx`/`fz`...),写成 `nEntity=`/`dFz=`/`node=` 会抛 `TypeError`
- `fz` 负值向下
- 端横梁/锚固点常用
- **同节点覆盖**:再 `create("NFORCE", 同节点, ...)` = 更新该节点力,不新增条目
- **局部只改某节点力**:改 `prep/_8_loadcase.py` 后按 `osis-engine` 跑 `prep/main.py`。

## 温度荷载(均匀/梯度)

**关键限制**:温度荷载的 `entity` 只能传 **int 单号**,**不支持 `'1to36'` 字符串区间**。必须用 for 循环逐个单元施加。

```python
# 均匀温度
lc = engine.load.create("整体升温", "T")
for i in range(1, 37):  # 显式循环
    lc.create_uniform_temperature(
        i,
        direct="X",                # "X"/"Y"/"Z"(X=整体升降温,Y/Z=横向梯度)
        temp=25,                   # 温差值(℃)
        length=None,               # Y/Z 方向长度,None = 自动通过截面计算
    )

# 梯度温度
lc = engine.load.create("梯度升温", "TG")
for i in range(1, 37):
    lc.create_gradient_temperature(
        i, "Z", "R", 2,            # entity, direct, g_temp_type, num —— 全部位置参数
        1.7, 0.0, 14, 0.1, 5.5, 1.7, 0.1, 5.5, 0.4, 0,  # *param 多组参数(varargs)
    )
```

> **签名**:`create_gradient_temperature(entity, direct="Y", g_temp_type="R", num=1, *param)`。
> `*param` 是 varargs,**关键字参数后面不能再跟位置参数**(Python 语法错误)——`entity`/`direct`/`g_temp_type`/`num` 要么全位置传,要么全关键字传,`*param` 永远位置传。

| 参数 | 含义 |
|---|---|
| `direct` | 局部方向("Y"/"Z") |
| `g_temp_type` | **定义梁的参考位置**:"R"/"T"/"C"/"B"(不是升温/降温!) |
| `num` | 折线段数,典型 2 |
| `*param` | 每段一组 `(B, H1, T1, H2, T2)`(宽度可空 `""`,H=距参考位置距离,T=该处温度) |

## 预应力绑定(钢束工况)

`create_prestress` 是 `loadcase` 模块内 `LoadCase` 对象的方法:

```python
# 由 tendon SKILL 创建的 prop + shape
engine.tendon.prop.create("15-15", "IN", mat=5, area=1, code="GBT5224_2014", diameter=15.2, num=15, pipe=0.09, ...)
shape = engine.tendon.shape.create_arc3d("BT3-y", n_num=2, prop="15-15", element_group="BT3-y_CurveGp", curve_name="BT3-y_Curve")
shape.layout("GLOBAL")

# loadcase 模块绑定到工况
lc = engine.load.create("预应力工况", "CS")
lc.create_prestress(
    entity="BT3-y",              # tendon shape 名
    tension_type="BOTH",         # "BOTH"/"BEG"/"END"
    tension_force_type="ST",     # "ST"/"IF"
    beg=1.395e9,                 # 起点应力/内力(Pa)
    end=1.395e9,                 # 终点应力/内力(Pa)
)
```

**字面量**:`tension_type ∈ {"BOTH", "BEG", "END"}`;`tension_force_type ∈ {"ST", "IF"}`。`beg`/`end` 单位是 **Pa**(1.395e9 Pa = 1395 MPa),不是 MPa。

**通用入口**:`lc.create("PST", <钢束shape名>, <tension_type>, <tension_force_type>, <beg>, <end>)` ≡ `lc.create_prestress(entity=<钢束shape名>, ...)`,与 `prop.create`/`shape.create` 的路由关系一致。模板命令流多用此形式。

**`entity` 是钢束 shape 名,不是工况名**:`"N1-1"` 这类 shape 名传给 `entity`;`"预应力腹板束"` 这类工况名只属于 `load.create` 与被 `_10` 的 `define_loadcase` 引用,两者不要混用。

> 预应力的添加**非常复杂**,完整的 4 步流程(prop → curve → shape → prestress)由 `osis-module-tendon` 处理,本模块只调最后一步。

## 报告状态

→ `osis-engine` §维护建模状态 表,本 module 写 `loads` 字段(工况名、类型映射、钢束工况、二期线荷载、温度值)。

**必须列出全部工况名的原样字符串清单**(如 `["预制单元自重", "预应力腹板束", "端横梁荷载工况", ...]`)。`_10_stage.py` 只许引用这张清单里的名字——这是本模块对 `_10` 的**契约**。桥型层给定的工况名(如 `预应力腹板束`/`预应力顶板束`)逐字使用,不得同义改写。

## 失败模式

- **`工况结果不存在,请先求解`** —— 施工阶段结果按单独工况名取;调 `osis-check` 做组合,不要直接 `result.loadcase()`
- **被 `_10` 引用时报"该工况中不存在名为 xxx"(命令流 `StgLC,...`)** —— `_10` 用了本模块没创建的名字。打开 `_8` 与 `_10` 两个文件对照工况名,改一侧到逐字一致,然后跑 `main.py` 写回。**禁止**不改代码直接重跑 `main.py`
- **温度荷载施加失败** —— `n_entity` 传了字符串区间;改成 for 循环
- **预应力不生效** —— `tendon.shape` 未 `layout('GLOBAL')`,或张拉力参数单位错(应该是 Pa,不是 MPa)
- **预应力报"形状控制点坐标超出参照单元组范围"** —— 钢束 x 跨入未激活单元,缩钢束端点

(其他见 `osis-engine/references/error_diagnosis.md`)

## 协作

| 上下游 | 交接 |
|---|---|
| 桥型层 → 本模块 | 二期恒载值、温度模式、特殊荷载(挂篮、湿重等) |
| 上游 `osis-module-element` | 单元范围(线荷载施加范围) |
| 上游 `osis-module-material` | 钢束材料号 |
| `osis-module-tendon` | 钢束 prop + shape + 锚固曲线(本模块只调 `create_prestress`) |
| 下游 `osis-module-stage` | 工况名(阶段激活引用) |
