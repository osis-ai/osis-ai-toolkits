# 截面变换

> `osis-module-section` 配套:`create_*` 参数化截面的尺寸缩放 + `create_custom` 的 contour_matrix 坐标变换。两种方法不可混用。

## 坐标系约定

```
Y=0 ───────── 截面横向中心(Middle)
Z=0 ───────── 顶面
Z 负方向 ──── 向下
```

所有 `create_*` 的 y、z 参数遵循此约定。`set_offset` 的 `offset_type_y="Middle"`、`offset_type_z="Top"` 是默认推荐。

---

## 参数化缩放(`create_*`)

### 核心约束

- `bc_l = bt_l - bb_l`(保证腹板垂直)
- `bs` 恒定 0.5(不随桥宽变)
- **从目标尺寸反推全部几何参数,不要只改 `h`/`bt`**

### 缩放示例:`create_conventionalbox`

```python
# 目标尺寸(唯一输入)
h, bt, bb = 1.5, 5.0, 3.0

# 推导
bc_l = bt - bb
bi1 = 2 * (bt - bc_l - 0.5) - 0.8

engine.section.create_conventionalbox(
    name,
    h=h, bt_l=bt, bt_r=bt, bb_l=bb, bb_r=bb,
    bs=0.5, tt=0.25, tb=0.22, tw1=0.5, tw2=0.5,
    n_cell_num=1, bi1=bi1,
    xi1=0.8, tt1=0.40, xi2=0, tt2=0,
    xi3=0.8, yi3=0.25, xi4=0.4, tt4=0.18,
    xi5=0.5, yi5=0.15, xi6=0.8, tt6=0.28,
    xi7=0.5, yi7=0.15,
    bc_l=bc_l, tc_l=0.18, bc1_l=0.8, tc1_l=0.45, tc2_l=0.25,
    b_symmetry=True, e_slope_type="Integral",
    no=no
)
```

### 几何检查不通过时的调整

微调 `bi1`(先降 0.2,再试)。若换用 `create_smallbox` 等其他 API,直接改参数值,无需走缩放流程。

### 常见缩放陷阱

- **只改 `h`** —— `tb`/`tw`/`bb` 不联动 → 几何检查不过
- **改 `bt` 但 `bc_l` 不动** —— 腹板不垂直
- **改 `bi1` 但 `bi2~bi4` 不联动** —— 多室截面宽度不自洽
- **横坡 `e_slope_type` 不动** —— 大跨桥改小跨后横坡不合理

---

## 自定义变换(`create_custom`)

参数化 API 无法表达时,使用 `create_custom` + `contour_matrix`。修改只能逐点变换,不能参数化。

### contour_matrix 结构

```python
contour = [
    [1,  y1, z1],   # 外轮廓点(逆时针)
    [1,  y2, z2],
    ...
    [2,  y1, z1],   # 内轮廓 1(腔室,顺时针)
    [2,  y2, z2],
    ...
    [3,  y1, z1],   # 内轮廓 2(腔室 2,顺时针)
    ...
]
engine.section.create_custom(name, matrix_name, no=no)
```

| 轮廓 ID | 含义 |
|---|---|
| 1 | 外轮廓 |
| 2, 3, ... | 内轮廓(各对应一个腔室) |

### 关键尺寸提取

| 尺寸 | 计算 |
|---|---|
| 顶宽 | 外轮廓最大 \|y\| × 2 |
| 梁高 | 外轮廓最小 z 的绝对值 |
| 悬臂长度 | 外轮廓最外侧点与腹板外缘的 y 差 |
| 顶板边缘厚 | 悬臂最薄处 z 的绝对值 |
| 顶板根部厚 | 腹板外缘 z 的绝对值 |
| 底板厚 | 腔室底部到底板底面的 z 差 |
| 室数 | 内轮廓数量 |

### 场景 1:跨径变化 → 仅调梁高

桥宽和室数不变,只改梁高。梁高估算:L/15 ~ L/18(跨径越大取值越小)。

**分区变换**(不能全 z 等比缩放):

| 区域 | z 范围 | 操作 |
|---|---|---|
| 顶板 | z ≥ -顶板根部厚 | 锁定不变 |
| 腹板 | -顶板根部厚 > z > -(h_old - 底板厚) | 拉伸,吃下全部梁高增量 |
| 底板 | z ≤ -(h_old - 底板厚) | 偏移到新底板位置,保持板厚 |

```python
h_old = 1.6
h_new = 2.0
t_top_root = 0.40
t_bot = 0.32
web_old = h_old - t_top_root - t_bot
web_new = h_new - t_top_root - t_bot

z_top_root = -t_top_root
z_bot_top_old = -(h_old - t_bot)
z_bot_bot_old = -h_old
z_bot_bot_new = -h_new

def transform(y, z):
    if z >= z_top_root:
        new_z = z
    elif z >= z_bot_top_old:
        frac = (z_top_root - z) / web_old
        new_z = z_top_root - frac * web_new
    else:
        offset = z - z_bot_bot_old
        new_z = z_bot_bot_new + offset
    return y, round(new_z, 4)
```

**y 坐标不变**(桥宽没改)。

### 场景 2:跨径+桥宽同时调整

y 方向也分区变换:

- 悬臂长度锁定不变
- 腹部 y 区域按比例拉伸,吸收全部宽度变化

```python
y_web_old = half_bt - cantilever
y_web_new = half_bt_new - cantilever

def transform_y(y):
    abs_y = abs(y)
    if abs_y <= y_web_old:
        new_abs = abs_y * (y_web_new / y_web_old)
    else:
        frac = (abs_y - y_web_old) / cantilever
        new_abs = y_web_new + frac * cantilever
    return new_abs if y >= 0 else -new_abs
```

### 场景 3:多个截面统一处理

模板通常有多个截面(跨中、墩顶加厚、变宽过渡等),全部用同一套变换规则处理。每个截面的 contour_matrix 分别变换后注册为不同的 matrix 名称。

### 注意事项

- 不要全 z 等比缩放 —— 板厚、倒角会变形
- 不要改内轮廓拓扑(三室→双室需要换模板,不能坐标变换)
- 点序和方向不变,只改坐标值
- 变换后验证:顶板厚、底板厚、悬臂长度需与原模板一致
- 注意不对称截面(边梁),y 变换要处理符号

---

## 缩放 vs 自定义变换决策表

| 场景 | 用法 |
|---|---|
| 改桥型尺寸(同截面形式) | 参数化 API 缩放 |
| 改梁高但保留拓扑 | 自定义截面 contour_matrix 分区变换 |
| 改室数(三室→双室) | 不能坐标变换,换模板 |
| 参数化 API 没有的目标类型 | 自定义截面 `create_custom` |

> ponytail: 参数化缩放覆盖 90% 场景,自定义变换仅在桥型层明确说"用 contour_matrix" 时启用。