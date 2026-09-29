---
name: osis-auto-testconformance
description: 桥梁构造建模正确性自动评测。在用户完成 `_1`..`_10` 模块建模(或模板套用)后,**自动**调用 `model_conformance` 评分器按桥型规则出分,生成总分 + D1~D5/D6 分项报告 + 状态(ok/warn/fail)。用于建模完工自检、模板套用核对、局部修改后验证——任何时候想确认"我做的这座桥构造是否合理"都用这个。不要和 `osis-check`(荷载/规范验算)混用。
---

# osis-auto-testconformance

> 建模完成后的自动构造正确性评测。**不需要用户主动调用**,写完 `_N_xxx.py` 后再跑一次本 SKILL 即可。
> 评测对象:当前 OSIS 项目 `py/` 下所有 `.py` 文件。规则来源:`src/evaluation/levels/model_conformance/`,按桥型路由。

## 定位

| 干 | 不干 |
|---|---|
| 评 `model_conformance` 一个维度(构造合理性) | 验算荷载组合 / 规范 → `osis-check` |
| 出总分 + D1~Dn 分项 + 状态 | 读 `.out` 结果 |
| 路由桥型 → 选对应规则 | 改任何代码(只读不写) |

## 工作流

```
调用方(建模 AI)显式给出:bridge_type / is_continuous
    │  ※ 桥型必须显式传;目录名识别(detect_bridge_type)只是兜底
    │    主跨 L 从节点/支座几何提取,不要从目录名猜
    ▼
扫 py/*.py → collect_python_files
    │
    ▼
调 _score_one → (overall, details)
    │
    ▼
调 generate_report → markdown
    │
    ▼
展示给用户：总分 + 各 D 项 + 状态 + 原因 + 建议
```

### 调用方必传的参数

| 参数 | 含义 | 取值 |
|---|---|---|
| `bridge_type` | 桥型 | cantilever_box / rigid_frame / t_girder / precast_small_box / cast_in_place_box / hollow_slab |
| `is_continuous` | 是否连续梁 | true / false |

可选:`expected_L`(仅当节点提取不到主跨时兜底)、`is_prestressed`、`concrete_ratio`、`beam_width`——知道就传,不传规则按代码提取值兜底。

## 用法 （CLI 推荐）

`scripts/` 下有 `test_conformance.py`(CLI)。

**标准模式(显式传桥型,推荐)**:
```bash
python scripts/test_conformance.py \
    --candidate-dir <path> \
    --bridge-type cantilever_box \
    --is-continuous true
```

**自动模式(兜底:从 OSIS 当前项目读 py/,桥型从目录名猜;主跨从节点提取)**:
```bash
python scripts/test_conformance.py
```

**只指定候选目录**(桥型仍从目录名猜,目录名不含信息时回退 unknown,分数可能失真):
```bash
python scripts/test_conformance.py --candidate-dir <path>
```

**支持的可选参数**:
- `--is-prestressed BOOL` — 是否预应力
- `--concrete-ratio FLOAT` — 混凝土折算厚度 m³/m²
- `--beam-width FLOAT` — 桥宽 m
- `--output PATH` — 报告写到文件(默认 stdout)
- `--no-auto-detect` — 桥型识别不出时报错,不用 unknown 兜底
- `--list-bridge-types` — 列支持的桥型并退出

**退出码**:`0` = 总分 ≥ 0.5(可接受);`1` = 总分 < 0.5(不通过,便于脚本判断)。

## 调用方式(直接 Python API,进阶)

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

from pyosis import OSISEngine
from model_conformance import (
    collect_python_files,
    _score_one,
    generate_report,
)

# 1. 定位当前 OSIS 项目
project = Path(OSISEngine().project.get_directory())
name = project.name
py_dir = project / "py"
if not py_dir.is_dir():
    raise SystemExit(f"未找到 {py_dir};请确认项目已建模")

# 2. 桥型/连续性:由建模 AI 显式给出(不要靠目录名猜跨径)
bridge_type = "cantilever_box"   # 7 桥型之一
is_continuous = True

# 3. 读候选代码
files = collect_python_files(py_dir)  # dict[relpath, text]

# 4. 评分(主跨 L 从节点提取;expected_L=None)
overall, details = _score_one(
    files,
    bridge_type=bridge_type,
    expected_L=None,
    is_continuous=is_continuous,
)

# 5. 出报告(generate_report 吃 evaluate 风格 dict,candidate 键下才是 details)
print(generate_report({"candidate": details, "bridge_type": bridge_type}, candidate_name=name))
print(f"\n>>> model_conformance 总分: {overall:.4f}  (满分 1.0)")
```

## 输出格式

markdown 报告大致形如:

```
# py 构造建模正确性评定报告

## 项目概况
- 候选目录: py
- 桥型: cantilever_box
- 主跨 L: 100.0 m
- 根部梁高 H_root: 6.5 m
- 跨中梁高 H_mid: 2.8 m
- 阶段数: 6
- 总分: 3.40 / 5.0
- 评级: 合格
- 与 reference 比值: 0.6800

## 分项检查
### 1. D1 跨径适配性: 1.00 / 1.0
- 状态: 符合要求

### 2. D2 高跨比: 0.00 / 1.0
- 状态: 不符合
- 原因: 跨中 H/L=1/35 偏小
- 建议: 取 1/18~1/20 区间
```

每 D 项末尾有 **状态**(`ok` ≥ 0.9 / `warn` ≥ 0.5 / `fail` < 0.5)+ **原因** + **建议**。

## 7 桥型分支

| 桥型 | 目录名兜底关键字 | 规则维度 |
|---|---|---|
| cantilever_box | 悬浇/悬臂 | D1–D5 |
| rigid_frame | 刚构 | D1–D6 |
| t_girder | T 梁 / 矮 T 梁 | D1–D4(按跨中马蹄自动分流:bh≤tw+2cm→矮T) |
| precast_small_box | 小箱梁 | D1–D4 |
| cast_in_place_box | 现浇箱梁 | 简化 5 维 |
| hollow_slab | 空心板 | D1–D5 |
| unknown | 不匹配任一 | 兜底 5 维(可能不准) |

上表关键字**仅供兜底**:调用方没传 `--bridge-type` 时,CLI 才用 `detect_bridge_type(目录名)` 猜。大多数用户目录名不含桥型信息,猜不中会回退 `unknown`,分数失真——所以建模 AI 调用时务必显式传参。

## 注意事项

- **必须先建模**:`py/` 是空的话所有 D 项 = 0,总分 0,无意义
- **桥型由 AI 传入**:`bridge_type` / `is_continuous` 由调用方显式传入;目录名解析(`detect_bridge_type`)只是没传参时的兜底
- **主跨从节点提取**:不要用目录名或 `spans_from_name` 猜 L
- **不修改代码**:只读不写,出错(`fail`)只汇报,不自动改
