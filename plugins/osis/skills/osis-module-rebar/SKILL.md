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

> 不在本模块决定钢筋数量是否足够 —— 那是验算的事。本模块只保证几何布置符合构造要求(保护层、最小间距等)。
>
> 钢筋通常直接写在 `_4_section.py` 里(截面建完后在对象上 `add_rebar_*`);只有变截面、多区段差异化配筋才单独维护。

## 布置方法

钢筋材料(如 `HRB400`)须先在 `osis-module-material` 建好,布置时引用材料号。参数用 `api_read` 查,要点:

| 方法 | 适合 |
|---|---|
| `add_rebar_line_a` | 参考位置 + 等间距的一排纵筋(顶板、底板纵筋) |
| `add_rebar_line_b` | 两端坐标定一排钢筋(斜向、腹板) |
| `add_rebar_point` | 单根钢筋(架立筋、补强) |
| `add_rebar_circle` | 圆周布置 |
| `add_rebar_s_shear_stirrup` / `_bent_up` / `_web_vertical` / `_torsional_stirrup` | 抗剪箍筋、弯起筋、腹板竖筋、扭转箍筋 |

- 间距参数名是 `interval`(不是 `int`);直径传字符串 `"D16"`。
- 删除用 `delete_rebar_l(rebar_no)` / `delete_rebar_s(<类型>)`。

## 抗剪类钢筋改参数

截面上**还没有**该类型时,首次 `add` 即可。模型里**已有**同类型时再 `add` 一次,HTTP 常仍成功、Python 无 traceback,但 OSIS 可能不更新,`section.get(no).rebar.has_shear_stirrup` 仍为 False 或仍是旧参数。改箍筋间距/直径:

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

## 失败模式

- **钢筋材料号不存在** —— `material_no` 不是 `osis-module-material` 已建的编号
- **截面对象不存在** —— `sec = engine.section.get(sec_no)` 返回 None,截面没在 `osis-module-section` 建出
- **保护层为负** —— `y_ref_value` 或 `z_ref_value` 设错,钢筋跑到截面外
- **改箍筋 EXIT=0 但 `has_shear_stirrup` 仍 False** —— 同类型二次 `add_rebar_s` 被 OSIS 静默丢掉。先 `delete_rebar_s` 再 add,读回 `section.get(no).rebar.has_shear_stirrup`

(其他见 `osis-engine/references/error_diagnosis.md`)

