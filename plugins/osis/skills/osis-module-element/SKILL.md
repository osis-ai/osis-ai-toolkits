---
name: osis-module-element
description: 单元建模模块。生成 `prep/_6_element.py`,创建梁单元和弹簧单元、建单元组、分配构件理论厚度。`_6` 建的组名被 `_8`(钢束投影)、`_9`(车道)、`_10`(阶段激活)按名引用。建哪些组、叫什么由桥型层和模板决定。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-element

> `prep/_6_element.py`:`build_elements(engine)`。

## 单元

```python
engine.element.create_beam3d(no, node1, node2, mat, sec1, sec2)   # 等截面两端同号,变截面两端不同
```

`no` 显式传。

**弹簧单元**(墩梁连接等)`create_spring(no, node1, node2, is_linear, dx, dy, dz, rx, ry, rz, beta)`:6 个方向刚度默认只有 10,**不传就不是固定**。固结时 `dx=dy=dz=1e13`、`rx=ry=rz=1e16`、`is_linear=1`。

## 单元组

组名是跨模块契约,下游按名引用,差一个字符就报"组不存在":

| 引用方 | 引用处 |
|---|---|
| `_8` 钢束 | `tendon.shape.create_*` 的 `element_group`(投影组) |
| `_9` 车道 | `live.lane.create_*` 的参照单元组 |
| `_10` 阶段 | `stage.define_element` 的组名 |

下游要用的组在 `_6` 一次建全。**钢束投影组要覆盖该钢束控制点 x 范围内的所有单元**,不够时 `layout("GLOBAL")` 报"控制点坐标超出参照单元组的坐标范围"。

```python
if engine.element.group.get("主梁单元"):
    engine.element.group.delete("主梁单元")        # 组删除无依赖检查,可直接用
eg = engine.element.group.create("主梁单元", "c")   # op 必填;不幂等,同名已存在报"单元组已经存在"
eg.add("1to46", "60to80")                          # varargs:int 或 "MtoN" 区间字符串,不传 list
```

- `add/remove/replace/rename` 在返回的 `ElementGroup` 对象上;manager 上没有 `add`。
- `create(name, "a", "11to18", "31to38")` 与对象 `add` 是同一条 `EleGrp` 命令。

## 构件理论厚度

用于收缩徐变计算,混凝土梁单元都要分配:

```python
engine.prop.assign_component_thickness(thickness, "a", 1, 2, "5to9")   # 单元编号 varargs
```

**op 用 `"a"`**(再次调用即覆盖);`"s"` 对已分配单元可能报「编辑构件厚度有误」。

### 怎么算

1. **截面**:`h_sec = 2A / (u_outer + u_in/2)`。`A` = 净混凝土面积(外轮廓面积 − 内腔面积);`u_outer` = 外轮廓周长;`u_in` = 全部内腔周长之和。内腔周长只计一半,不是 `u_outer + u_in`;没有内腔的截面就是 `2A / u_outer`。
2. **单元**:`h_elem = (h_sec(sec1) + h_sec(sec2)) / 2`,变截面单元取两端平均。
3. `h_elem` 相同的单元收成一批,一次 `assign_component_thickness`。

`section.get(no).prop` 常为 `None`,A 和周长用轮廓自己算:

```python
import math
rings = engine.section.get(no).contour   # list[list[{x,y}]]; [0]=外轮廓,其后=内腔(一个内腔可能被拆成几段,周长相加)

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

- 自检:改截面前先对已有截面算一次,应与 `_6` 里现有厚度一致(末位舍入差除外);对不上先查轮廓环数和平均规则。
- **改了梁高、板厚或桥宽就要重算**并写回 `_6`。先让 `_4` 的新截面进 OSIS,再读 `contour`。只改跨径、截面没变时,厚度值不用动。

## 失败模式

- **`组不存在` / `load group not found`** —— 下游引用的组名没建,或大小写/下划线/前缀不一致
- **`弹性连接报错`** —— 弹簧刚度没传(默认 10)或 `is_linear=0`;或 `_10` 激活弹簧单元组时 `birth` 不是 0
