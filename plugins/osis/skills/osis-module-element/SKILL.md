---
name: osis-module-element
description: 单元建模模块。生成 `prep/_6_element.py`,创建梁单元、分配材料/截面、组建分组。处理"组名 = 跨模块契约"的核心规则——`_6` 创建的组名被 `_8`(钢束投影)、`_9`(车道引用)、`_10`(阶段激活)三处引用,任一处差一个字就报"组不存在"。**具体建哪些组、组名清单由桥型层 SKILL 决定**,本模块负责按清单建组并保证跨模块命名一致。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-element

> 单元模块。负责把节点连成梁单元,按用途建分组。分组命名是跨模块协作的关键契约。

## 接到任务后,按顺序做

1. **从建模状态读取**:节点编号、截面编号、材料编号。
2. **创建梁单元**(`create_beam3d`),逐对节点连线,显式指定 `no`、`mat`、`sec1`/`sec2`。
3. **组建分组**(`element.group.create`)。下游要用的组在本模块一次建好,不能"用到再建"。
4. **分配构件理论厚度**(`prop.assign_component_thickness`),见 §分配构件理论厚度。
5. **把单元编号、分组名写入建模状态**。

## 单元创建

```python
engine.element.create_beam3d(no, node1, node2, mat, sec1, sec2)   # 等截面两端同号,变截面两端不同
```

- `node1`/`node2`、`mat`、`sec1`/`sec2` 必须是 `_5`/`_3`/`_4` 已建的对象
- 单元编号 `no` 显式传,建议从 1 起连续编号

**弹簧单元**(墩梁连接等)`create_spring(no, node1, node2, is_linear, dx, dy, dz, rx, ry, rz, beta)`:6 个方向刚度默认只有 10,**不传就不是固定**。固结时 `dx=dy=dz=1e13`、`rx=ry=rz=1e16`、`is_linear=1`。

## 组名 = 跨模块契约

| 引用方 | 用途 | 引用参数 |
|---|---|---|
| `_8_loadcase`(钢束) | 钢束投影 | `tendon.shape.create_*` 的 `element_group` |
| `_9_analysis`(车道) | 车道引用 | `live.lane.create_*` 的 `ref_elems` |
| `_10_stage`(阶段) | 阶段激活 | `stage.define_element` 的组名 |

任一处差一个字符(中文/下划线/数字/大小写)就报"组不存在"或"load group not found"。建好后立即写入状态,下游照状态里的组名原样用,不要另起新名、改大小写、删前缀。

具体组名由桥型层决定,按用途分三类:

| 用途 | 引用方 | 命名风格 |
|---|---|---|
| 施工构件 | `_10_stage` | 描述用途/位置的中文名 |
| 钢束投影 | `_8_loadcase` | 钢束名 + `CurveGp` / `Gp` |
| 车道引用 | `_9_analysis` | 描述位置的中文名(常 `主梁单元`) |

**钢束投影组**必须覆盖钢束控制点 x 范围内的所有单元;范围不足时 `tendon.shape.layout('GLOBAL')` 报"控制点坐标超出参照单元组的坐标范围"。

## 建组

```python
if engine.element.group.get("主梁单元"):
    engine.element.group.delete("主梁单元")   # 组删除无依赖检查,可直接用
eg = engine.element.group.create("主梁单元", "c")   # op 必填
eg.add("1to46", "60to80")                        # varargs:int 或 "MtoN" 区间字符串,不传 list
```

- `create(name, "c")` 不幂等:同名组已存在时报"单元组已经存在",所以先 delete-if-exists(见 `osis-engine/references/incremental_rerun.md`)。
- `add/remove/replace/rename` 在返回的 `ElementGroup` 对象上调;manager 上没有 `add`,调了抛 `AttributeError`。
- `add` 的类型标注写的是 int,但字符串区间也能用。
- 等价写法 `create(name, "a", "11to18", "31to38")`(`.out` 直译风格)与对象 `add` 是同一条 `EleGrp` 命令。

## 分配构件理论厚度

```python
engine.prop.assign_component_thickness(thickness, "a", 1, 2, "5to9")   # 单元编号 varargs
```

- 理论厚度用于收缩徐变计算,混凝土梁单元必须分配。
- **op 用 `"a"`**(再次调用即覆盖)。`"s"` 对已分配单元可能报「编辑构件厚度有误」。

### 公式(箱梁 / CONVENTIONALBOX)

1. **截面**:`h_sec = 2A / (u_outer + u_in/2)`
   - `A` = 净混凝土面积(外轮廓面积 − 各内腔面积之和)
   - `u_outer` = 外轮廓周长;`u_in` = **全部**内腔周长之和(接口若把一个内腔拆成左右两段,周长相加)
   - 不是 `u_outer + u_in`
2. **单元**:`h_elem = (h_sec(sec1) + h_sec(sec2)) / 2`。等截面单元即 `h_sec`;变截面单元必须取两端平均,不能只拿一端。
3. **分批赋值**:`h_elem` 相同的单元收成一组,一次 `assign_component_thickness`。相邻节段值不同是正常的。

### 取 A、u

`section.get(no).prop` 常为 `None`,不要等面积/周长字段;用轮廓自己算:

```python
import math
rings = engine.section.get(no).contour   # list[list[{x,y}]]; [0]=外轮廓,其后=内腔

def _area_peri(pts):
    xs = [p["x"] for p in pts] + [pts[0]["x"]]
    ys = [p["y"] for p in pts] + [pts[0]["y"]]
    a = u = 0.0
    for i in range(len(pts)):
        a += xs[i] * ys[i + 1] - xs[i + 1] * ys[i]
        u += math.hypot(xs[i + 1] - xs[i], ys[i + 1] - ys[i])
    return abs(a) / 2.0, u

A_out, u_outer = _area_peri(rings[0])
A_in = u_in = 0.0
for ring in rings[1:]:
    a, u = _area_peri(ring)
    A_in += a
    u_in += u
h_sec = 2 * (A_out - A_in) / (u_outer + u_in / 2)
```

自检:改截面前先对已有截面算一次,应与 `_6` 里现有厚度一致(允许末位舍入差);对不上先查轮廓环数和平均规则。

### 何时重算

- 改了梁高、板厚或桥宽 → A、u 全变,按上式重算后写回 `_6`,不能沿用旧值。
- 时机:`_4` 截面已在 OSIS 中创建/更新后再读 `contour`。
- 写回按 `osis-engine` §写回(单跑 `_6` 或 `main.py`)。

## 失败模式

- **`组不存在` / `load group not found`** —— 下游引用的组名没建,或大小写/下划线/前缀不一致。对照状态里的组名清单
- **`形状控制点坐标超出参照单元组的坐标范围`** —— 钢束投影组范围不足,扩组范围
- **弹簧报"弹性连接报错"** —— 刚度没传(默认 10)或 `is_linear=0`

(其他见 `osis-engine/references/error_diagnosis.md`)
