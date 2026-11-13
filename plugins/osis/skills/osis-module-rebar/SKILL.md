---
name: osis-module-rebar
description: 普通钢筋建模模块。在已建截面上布置普通钢筋(纵筋、箍筋、弯起筋、腹板竖筋、点筋)。用户要配筋、改箍筋,或验算需要钢筋时使用。只布置,不验算。
---

# osis-module-rebar

> 钢筋方法全部在 **Section 对象**上调,没有单独的 rebar manager:`sec = engine.section.get(sec_no)`,再 `sec.add_rebar_*`。通常直接写在 `_4_section.py` 里截面建完之后。配多少由项目和验算定。

## 布置方法

钢筋材料先在 `_3` 建好,布置时引用材料号。参数用 `api_read` 查。

| 方法 | 适合 |
|---|---|
| `add_rebar_line_a` | 参考位置 + 等间距的一排纵筋(顶板、底板纵筋) |
| `add_rebar_line_b` | 两端坐标定一排钢筋(斜向、腹板) |
| `add_rebar_point` | 单根钢筋 |
| `add_rebar_circle` | 圆周布置 |
| `add_rebar_s_shear_stirrup` / `_bent_up` / `_web_vertical` / `_torsional_stirrup` | 抗剪箍筋、弯起筋、腹板竖筋、扭转箍筋 |

- 间距参数名是 `interval`(不是 `int`);直径传字符串 `"D16"`。
- 删除用 `delete_rebar_l(rebar_no)` / `delete_rebar_s(<类型>)`。
- 腹板竖筋(竖向预应力)的 `effective_stress` 单位是 Pa:567.4 MPa 写 `5.674e8`。
- `add_rebar_l` 同编号是覆盖。

## 抗剪类钢筋改参数

截面上**已有**同类型时再 `add` 一次,调用成功、没有 traceback,但 OSIS 不更新。先删再加,并读回:

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

弯起筋、腹板竖筋、扭转箍筋同理:`delete_rebar_s(<类型>)` 再 add,用对应的 `has_*` 读回。

## 失败模式

- **钢筋跑到截面外** —— `y_ref_value` / `z_ref_value` 设错
- **`section.get(no)` 返回 None** —— 截面还没建
