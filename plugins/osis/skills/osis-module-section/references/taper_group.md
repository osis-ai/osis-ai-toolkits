# 变截面组(TaperEle)

OSIS 通过 TaperEle 命令在两端截面之间自动生成中间截面序列,避免手工建大量中间截面。

## 工作原理

1. 创建两端截面(如 1 号=深,2 号=浅)
2. 整组单元赋予相同 `nSec1`/`nSec2`(变截段统一用浅→深或深→浅)
3. 调用 `engine.element.taper_group.create(...)` 注册
4. OSIS 自动生成大量中间截面,命名如 `408_组1_408`

## 重要限制

1. **只支持 9 种参数化截面类型**:L 型/倒 L 型、T 型/倒 T 型、工字型、圆/圆管形、实心/空腹矩形(可倒圆/斜角)、实心/空腹圆端形、小箱梁、T 梁、常规箱梁
2. **不支持自定义截面**(`create_custom`)
3. **整组单元必须拥有相同的截面号和过渡形式**(`nSec1`、`nSec2`、`nZTrans`、`nYTrans` 必须一致)
4. TaperEle 命令在导出命令流时会被注释 —— OSIS 实际使用自动生成的独立截面

## pyosis API

```python
engine.element.taper_group.create(
    name,        # str: 组名
    z_type,      # int: 0=线性, 1=多项式
    z_trans=1.0, # float: 过渡参数(多项式时为指数,2.0=二次,1.6=1.6次)
    z_pos=0,     # int: 0=I 端, 1=J 端
    z_dis=0.0,   # float: Z 向对称面距
    y_type=0,    # int: 0=线性, 1=多项式
    y_trans=1.0, # float: Y 向过渡参数
    y_pos=0,     # int: 0=I 端, 1=J 端
    y_dis=0.0,   # float: Y 向对称面距
    *eles,       # int|str|list: 单元范围
)
```

| 参数 | 含义 | 取值 |
|---|---|---|
| `name` | 变截面组名称 | 任意 |
| `z_type` | Z 向过渡类型 | 0=线性,1=多项式 |
| `z_trans` | Z 向过渡参数 | 线性=1.0,多项式=指数 |
| `z_pos` | Z 向哪端贴平(斜率=0),同时决定凹向 | 0=I 端,1=J 端 |
| `z_dis` | Z 向对称面距 | 通常 0.0 |
| `y_type` | Y 向过渡类型 | 0=线性,1=多项式 |
| `y_trans` | Y 向过渡参数 | 线性=1.0 |
| `y_pos` | Y 向参考位置 | 0=I 端,1=J 端 |
| `y_dis` | Y 向对称面距 | 通常 0.0 |
| `*eles` | 组内单元 | `4to49` / `1,3,5` / `[1,2,3]` |

## 抛物线凹向控制

| 梁高变化 | `z_pos` | 效果 |
|---|---|---|
| 深→浅(递减) | 0 | 梁底朝**下鼓**(深端贴平) |
| 深→浅(递减) | 1 | 梁底朝**上凹**(浅端贴平) |
| 浅→深(递增) | 0 | 梁底朝**上凹**(浅端贴平) |
| 浅→深(递增) | 1 | 梁底朝**下鼓**(深端贴平) |

**口诀**:`z_pos` 和"深端"同侧 → 朝下鼓;`z_pos` 和"浅端"同侧 → 朝上凹。

## 实战 —— 2×20m 连续梁(中间深、两端浅)

```
x=0 ── [浅等截] ── [浅→深 抛物线] ── [深等截] ── [深→浅 抛物线] ── [浅等截] ── x=40
```

```python
# 1. 截面
sec_deep = engine.section.create_smallbox("深截面", h=2.0, ..., no=1)
sec_shallow = engine.section.create_smallbox("浅截面", h=1.4, ..., no=2)

# 2. 单元(等截段用相同 nSec1/nSec2,变截段统一用浅→深或深→浅)
D, S = sec_nos[0], sec_nos[1]
assignments = []
assignments += [(S, S)] * 2    # 左端等截面
assignments += [(S, D)] * 16   # 变截过渡 浅→深
assignments += [(D, D)] * 4    # 中支点等截面
assignments += [(D, S)] * 16   # 变截过渡 深→浅
assignments += [(S, S)] * 2    # 右端等截面

for i, (s1, s2) in enumerate(assignments):
    engine.element.create_beam3d(
        i+1, i+2, nMat=1, nSec1=s1, nSec2=s2, nZTrans=1, nYTrans=1, no=i+1
    )

# 3. 变截面组(只覆盖变截段,不含等截面段)
engine.element.taper_group.create(
    "变截面-左", 1, 2.0, 0, 0.0, 0, 1.0, 0, 0.0, "3to18"   # 浅→深 z_pos=0
)
engine.element.taper_group.create(
    "变截面-右", 1, 2.0, 1, 0.0, 0, 1.0, 0, 0.0, "23to38"  # 深→浅 z_pos=1
)
```

## 与 `create_beam3d(nZTrans=2)` 的区别

| 维度 | 单单元 `nZTrans=2` | 变截面组 TaperEle |
|---|---|---|
| 作用范围 | 单个单元内部 | 整组单元 |
| 中间截面 | 无(直接插值计算) | OSIS 自动生成大量独立截面 |
| 截面类型限制 | 无限制 | 仅 9 种参数化类型 |
| 命令流导出 | 正常导出 | 被注释,用独立截面替代 |