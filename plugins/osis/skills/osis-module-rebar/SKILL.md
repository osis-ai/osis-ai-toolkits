---
name: osis-module-rebar
description: 普通钢筋建模模块。在已建截面上布置普通钢筋(纵筋、箍筋、架立筋、点筋)。处理边梁/中梁区分、顶/底板/腹板分区、保护层与构造要求。当总控加载 `osis-module-section` 后,需要在该截面上补钢筋时使用。本模块只布置几何,不验算。
---

# osis-module-rebar

> 钢筋模块。在已建截面对象上布置几何,不验算。

## 公共约定

**钢筋方法全部在 Section 对象上调**,不是单独的 rebar manager。先 `sec = engine.section.get(sec_no)` 拿到截面对象,再在对象上调 `add_rebar_*` 系列。

## 接到任务后,按顺序做

1. **从 `profile` + 截面状态读取**:截面编号、钢筋等级(已在 `osis-module-material` 建)、保护层、构造要求。
2. **确定钢筋布置方案**:边梁/中梁、顶/底板/腹板分区、纵筋/箍筋/架立筋根数。
3. **逐根/逐区域添加钢筋**(`add_rebar_line_a` / `add_rebar_line_b` / `add_rebar_point` / `add_rebar_s_shear_stirrup`)。
4. **把钢筋布置事实写入建模状态**(`sections` 字段的子项)。

> 不在本模块决定钢筋数量是否足够 —— 那是验算模块的事。本模块只保证几何布置符合构造要求(保护层、最小间距等)。

## 钢筋材料前置

钢筋材料(`HRB400` / `HRB500` / `HPB300`)必须先在 `osis-module-material` 中创建并分配材料号。布置时引用材料号:

```python
sec = engine.section.get(sec_no)   # 拿截面对象
# 引用 osis-module-material 中已建的钢筋材料号
```

## 4 种纵向钢筋布置方法

### 沿线 a:两点 + 等间距

```python
sec.add_rebar_line_a(
    rebar_no,                    # 钢筋编号
    material_no,                 # 钢筋材料号
    y_ref="Left",                # Y 方向参考:"Left"=左 / "Center"=质心
    y_ref_value=0.0,             # 距 Y 参考位置的距离(Y 轴正方向为正)
    z_ref="Top",                 # Z 方向参考:"Top"=顶 / "Bottom"=底
    z_ref_value=0.0,             # 距 Z 参考位置的距离(Z 轴正方向为正)
    num=1,                       # 数量
    interval=0.1,                # 间距(m)(不是 "int"!)
    diameter="D16",              # 钢筋直径,D4~D50
)
```

适合**单段直线钢筋**(顶板纵筋、底板纵筋)。

### 沿线 b:两端坐标

```python
sec.add_rebar_line_b(
    rebar_no,
    material_no,
    start_y=0.0,                 # 起点 Y 坐标
    start_z=0.0,                 # 起点 Z 坐标
    end_y=0.0,                   # 终点 Y 坐标
    end_z=0.0,                   # 终点 Z 坐标
    method=1,                    # 1=输入数量 / 0=输入间距
    num=1,
    interval=0.1,
    layout_ref="StartPoint",     # "StartPoint"/"MidPoint"/"EndPoint"
    has_end_rebar=1,             # 1=有端筋 / 0=无端筋
    diameter="D16",
)
```

适合**两点带方向的钢筋**(腹板箍筋、弯起钢筋)。

### 点筋

```python
sec.add_rebar_point(
    rebar_no,                    # 钢筋编号
    material_no,                 # 材料号
    coor_y=0.0,                  # 中心点 Y 坐标
    coor_z=0.0,                  # 中心点 Z 坐标
    diameter="D16",
)
```

适合**单点钢筋**(架立筋、加密区补强)。

### 圆周输入

```python
sec.add_rebar_circle(
    rebar_no, material_no,
    center_y, center_z, radius,
    method, num, interval, diameter,
)
```

## 通用入口 `add_rebar_l`

按 `type` 派发到上面 4 种纵向钢筋方法:

```python
sec.add_rebar_l(rebar_no, type, *args)
# type: "Point" / "LineA" / "LineB" / "Circle"
```

`add_rebar_l` / `add_rebar_s` 与具体 `add_rebar_*` 方法的关系,同其他模块的 `create()` / `create_*`:通用入口只多一个 `type` 路由参数,其余参数(顺序、含义、默认值)与对应的具体方法完全一致。

## 抗剪钢筋(沿截面周长自动生成)

```python
# 抗剪箍筋(腹板箍筋一键布置)
sec.add_rebar_s_shear_stirrup(
    material_no,                 # 钢筋材料号
    interval=0.15,               # 间距(m)
    area=1.13e-4,                # 单肢面积(m²,D12)
)
```

截面上**还没有**该类型时,首次 `add` 即可。模型里**已有**同类型(模板默认 D10、或上次已写入)时再 `add` 一次,HTTP 常仍成功、Python 无 traceback,但 OSIS 可能不更新,`section.get(no).rebar.has_shear_stirrup` 仍为 False 或仍是旧参数。改箍筋间距/直径:

```python
sec = engine.section.get(no)
try:
    sec.delete_rebar_s("ShearStirrup")
except RuntimeError:
    pass
sec.add_rebar_s_shear_stirrup(material_no, interval, area)
if not engine.section.get(no).rebar.has_shear_stirrup:
    raise RuntimeError(f"截面 {no} 抗剪箍筋未写入")
```

弯起/腹板竖筋/扭转箍筋同类:`delete_rebar_s(<类型>)` 再 add,用对应 `has_*` 读回。`add_rebar_l` 同编号走覆盖语义,不在此列。

```python
# 弯起钢筋
sec.add_rebar_s_bent_up(material_no, interval, area, angle)

# 腹板竖筋
sec.add_rebar_s_web_vertical(material_no, interval, area, angle, effective_stress, reduction_factor)

# 扭转箍筋
sec.add_rebar_s_torsional_stirrup(material_no, interval, longi_area, stirrup_area)
```

## 通用入口 `add_rebar_s`

```python
sec.add_rebar_s(type, *args)
# type: "BentUpRebar" / "ShearStirrup" / "WebVerticalRebar" / "TorsionalStirrup"
```

## 删除钢筋

```python
sec.delete_rebar_l(rebar_no)                            # 删除指定编号的纵向钢筋
sec.delete_rebar_s("ShearStirrup")                       # 删除指定类型箍筋
```

## 按桥型/位置的典型钢筋方案

不同桥型/位置的钢筋方案由桥型层 SKILL 决定,本模块不规定。本节列出**通用模式**作为参考。

### 中梁(标准截面,任何桥型)

- 顶板纵筋:HRB400,Φ16 或 Φ20,等间距布置
- 底板纵筋:HRB400,Φ16 或 Φ20,等间距布置
- 腹板箍筋:HRB400,Φ12,间距 0.15m(关键) / 0.2m(标准)
- 保护层:50mm(外层)/ 30mm(内层)

### 边梁(任何桥型)

- 与中梁类似,但**外侧保护层更大**(60mm),内侧不变
- 悬臂部分加密钢筋

### 箱梁顶/底板(任何桥型)

- 顶板上下层纵筋 + 横向分布筋
- 底板上下层纵筋
- 腹板内外箍筋

## 保护层与构造

| 位置 | 保护层 |
|---|---|
| 主梁外层 | 50~60mm |
| 主梁内层(箱室) | 30~40mm |
| 桥面板 | 40mm |
| 桥墩 | 50~70mm |

**构造要求**(由规范给出,本模块只保证参数化布置符合):

- 纵筋最小净距 ≥ 直径或 25mm(取大值)
- 箍筋间距 ≤ 梁高/2 且 ≤ 250mm
- 加密区箍筋间距 ≤ 100mm(支点附近)

## 报告状态

→ `osis-engine` §维护建模状态 表,本 module 写 `sections` 字段子项(截面编号 → 钢筋方案、保护层、加密区、钢筋等级引用)。

## 失败模式

- **钢筋材料号不存在** —— `material_no` 不是 `osis-module-material` 已建的编号
- **截面对象不存在** —— `sec = engine.section.get(sec_no)` 返回 None,截面没在 `osis-module-section` 建出
- **保护层为负** —— `y_ref_value` 或 `z_ref_value` 设错,钢筋跑到截面外
- **箍筋 method=0 但有弯折** —— 弯起钢筋必须 `method=1`
- **改箍筋 EXIT=0 但 `has_shear_stirrup` 仍 False** —— 同类型二次 `add_rebar_s` 被 OSIS 静默丢掉。先 `delete_rebar_s` 再 add,读回 `section.get(no).rebar.has_shear_stirrup`

(其他见 `osis-engine/references/error_diagnosis.md`)

## 协作

| 上下游 | 交接 |
|---|---|
| 上游 `osis-module-section` | 截面编号(钢筋依附的对象) |
| 上游 `osis-module-material` | 钢筋材料号(`material_no` 引用) |
| 桥型层 → 本模块 | 钢筋方案(等级、直径、间距、保护层) |
| 下游 `osis-check`(工具层) | 钢筋数据消费方(验算用) |

> 实践:本 module 通常合并到 `_4_section.py` 的 `add_rebar_*` 调用,不单独建 `_4_rebar.py`。仅变截面、多区段差异化配筋单独维护。

## 备注:本模块通常与 section 合并

工程实践中,钢筋布置通常直接写在 `_4_section.py` 中(在截面对象上 add_rebar),不单独建 `_4_rebar.py`。本 SKILL 用于**较复杂配筋**(变截面、多区段差异化)或**单独维护钢筋方案**的场景。简单情况直接 `osis-module-section` 末尾追加 `add_rebar_*` 即可。
