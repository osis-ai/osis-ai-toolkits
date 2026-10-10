---
name: osis-module-loadcase
description: 荷载工况模块。生成 `prep/_8_loadcase.py`,创建工况(自重/二期/温度/线荷载/节点力),施加各类荷载。处理工况类型选择、温度荷载的逐单元循环约束、预应力钢束的工况绑定。当总控按依赖顺序加载到本模块时使用。钢束的 prop/shape 仍由 `osis-module-tendon` 负责。
---

# osis-module-loadcase

> 荷载工况模块。决定有哪些工况、每种工况施加什么荷载。

## 接到任务后,按顺序做

1. **从 `profile` + 桥型层读取**:二期恒载值、温度模式、特殊荷载、是否含预应力。
2. **创建工况**(`load.create(name, load_case_type, scalar)`),返回 `LoadCase` 对象。
3. **在 LoadCase 对象上施加荷载**(`create_gravity` / `create_line_load` / `create_nforce` / `create_uniform_temperature` / `create_gradient_temperature` / `create_prestress`;不是在 manager 上)。
4. **把全部工况名写入建模状态**(见 §工况名契约)。

> 钢束的 prop/shape 创建属 `osis-module-tendon`;本模块只调 `create_prestress` 把它绑到工况。

## 工况类型

可选值用 `api_read` 看 `load.create` 的 `load_case_type`。易错点:

- **自重、二期、预应力都用 `CS`**;均匀温度 `T`、梯度温度 `TG`。
- `SH` = 收缩、`CR` = 徐变,不要记反;沉降类用 `STL`,不是 `EV`。

```python
lc = engine.load.create("主梁自重", "CS", 1.0)
lc.create_gravity(x_coeff=0, y_coeff=0, z_coeff=-1.04)
```

## 荷载要点

**通用**:参数名一律 snake_case(`x_coeff`、`entity`、`fz_i`…),camelCase 会抛 `TypeError`。很多参数的默认值不是 0,**用到的方向全部显式传**。

- **自重** `create_gravity`:`x_coeff`/`y_coeff` 默认是 1.0,必须显式传 0。系数乘 g,负=向下;默认 `z_coeff=-1.04`(1.04 计入钢筋等超重)。
- **线荷载** `create_line_load`:`coord_system` 默认 1(整体)、`load_type` 默认 1(离散)、`fx_i`/`fy_i` 默认 100,都要显式传。满布写 `load_type=0, offset_x_i=0, offset_x_j=1`。`entity` 只接受单个单元号,多单元用循环。
- **节点力** `create_nforce(entity, fx, fy, fz, mx, my, mz)`:`fx` 默认 100,显式传 0。等价便捷写法 `lc.create("NFORCE", node, fx, fy, fz, mx, my, mz)`。同节点再建 = 更新该节点力,不新增条目。

## 温度荷载

`entity` 只能传 **int 单号**,不支持 `'1to36'` 区间,必须逐单元循环:

```python
lc = engine.load.create("整体升温", "T")
for i in elems:
    lc.create_uniform_temperature(i, direct="X", temp=20)   # X=整体升降温

lc = engine.load.create("正温度梯度", "TG")
for i in elems:
    lc.create_gradient_temperature(
        i, "Z", "R", 2,                                # entity, direct, g_temp_type, num —— 全部位置传
        1.7, 0.0, 14, 0.1, 5.5, 1.7, 0.1, 5.5, 0.4, 0,  # *param
    )
```

- `*param` 是 varargs,**关键字参数后不能再跟位置参数**:前 4 个参数全位置传。
- `g_temp_type` 是**梁的参考位置**("R"/"T"/"C"/"B"),不是升温/降温。
- `num` = 折线段数;`*param` 每段一组 `(B, H1, T1, H2, T2)`(B 可空 `""`,H=距参考位置距离,T=该处温度)。

## 预应力绑定

```python
lc = engine.load.create("预应力工况", "CS")
lc.create_prestress(
    entity="BT3-y",              # 钢束 shape 名,不是工况名
    tension_type="BOTH",         # "BOTH"/"BEG"/"END"
    tension_force_type="ST",     # "ST"/"IF"
    beg=1.395e9, end=1.395e9,    # 单位 Pa(1.395e9 Pa = 1395 MPa)
)
```

- 等价写法 `lc.create("PST", <shape名>, <tension_type>, <tension_force_type>, <beg>, <end>)`。
- `entity` 传 shape 名(如 `"N1-1"`);工况名(如 `"预应力腹板束"`)只用于 `load.create` 和 `_10` 的 `define_loadcase`,两者不要混用。
- prop → curve → shape 的前置流程见 `osis-module-tendon`。

## 工况名契约

建模状态里**列出全部工况名的原样字符串清单**(如 `["预制单元自重", "预应力腹板束", "端横梁荷载工况", ...]`)。`_10_stage.py` 只许引用这张清单里的名字。桥型层给定的工况名逐字使用,不得同义改写。

## 失败模式

- **`工况结果不存在,请先求解`** —— 施工阶段结果按单独工况名取;组合用 `osis-check`,不要直接 `result.loadcase()`
- **被 `_10` 引用时报"该工况中不存在名为 xxx"(命令流 `StgLC,...`)** —— `_10` 用了本模块没创建的名字。对照 `_8` 与 `_10` 的工况名,改一侧到逐字一致后写回
- **温度/线荷载施加失败** —— `entity` 传了字符串区间;改成循环
- **自重方向不对** —— `create_gravity` 没传 `x_coeff=0, y_coeff=0`,用了默认 1.0
- **预应力不生效** —— `tendon.shape` 未 `layout('GLOBAL')`,或张拉力单位错(应为 Pa)
- **预应力报"形状控制点坐标超出参照单元组范围"** —— 钢束 x 超出投影组覆盖的单元,缩钢束端点或扩组

(其他见 `osis-engine/references/error_diagnosis.md`)
