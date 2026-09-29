# `tendon.prop` 签名

`create()` 按 `(s_type, area)` 派发到 `create_*`。`create()` 比具体方法多 `s_type`、`area` 两个路由参数,其余参数一致。

- `s_type`:`"IN"` 后张体内 / `"EX"` 后张体外 / `"PRE"` 先张
- `area`:`1` 按规范 / `0` 用户输入面积

体内按规范:

```python
engine.tendon.prop.create(
    name="15-15",
    s_type="IN",
    mat=5,
    area=1,
    code="GBT5224_2014",
    diameter=15.2,
    num=15,
    pipe=0.09,
    friction_coeff=0.17,
    deviation_coeff=0.0015,
    starting_deform=0.006,
    end_deform=0.006,
    tensioning_coeff=1.0,
    relaxation_coeff=0.30,
)
```

等价于:

```python
engine.tendon.prop.create_in(
    name="15-15",
    mat=5,
    code="GBT5224_2014",
    diameter=15.2,
    num=15,
    pipe=0.09,
    friction_coeff=0.17,
    deviation_coeff=0.0015,
    starting_deform=0.006,
    end_deform=0.006,
    tensioning_coeff=1.0,
    relaxation_coeff=0.30,
)
```

即 `create("15-15", "IN", 5, 1, code="GBT5224_2014", diameter=15.2, num=15, pipe=0.09)` ≡ `create_in("15-15", 5, code="GBT5224_2014", diameter=15.2, num=15, pipe=0.09)`。

| 参数 | 含义 |
|---|---|
| `name` | 规格名,常用 `'15-N'`(N=股数) |
| `mat` | `_3` 预应力材料号 |
| `code` | `GBT5224_2014` 或 `GBT20065_2016`(`area=1` 必填) |
| `diameter` | 单股直径(mm) |
| `num` | 每股根数 |
| `pipe` | 管道直径(m) |
| `friction_coeff` | 摩擦系数 |
| `deviation_coeff` | 偏差系数 |
| `starting_deform` / `end_deform` | 锚具回缩(m) |
| `tensioning_coeff` | 张拉系数 |
| `relaxation_coeff` | 松弛系数 |
