---
name: osis-auto-testconformance
description: 桥梁构造建模正确性自动评测。在用户完成 `_1`..`_10` 模块建模(或模板套用)后,**自动**调用 `model_conformance` 评分器按桥型规则出分,生成总分 + D1~D5 分项报告 + 状态(ok/warn/fail)。用于完整建模(含模板复制/小修)完工后的自检;用户要求确认"这座桥构造是否合理"时也用这个。不要和 `osis-check`(荷载/规范验算)混用。
---

# osis-auto-testconformance

> 完整建模(含模板复制/小修)写回成功后,由总控自动跑一次,不需要用户开口;"越快越好"也不省略。局部修改、`osis-edit-hmid` 不跑,除非用户要求。
> 评测对象:当前 OSIS 项目 `py/` 下所有 `.py` 文件。规则在本 skill 的 `scripts/model_conformance/`,按桥型路由。

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

`scripts/` 下有 `test_conformance.py`(CLI;`<skill_dir>` = 本 SKILL.md 所在目录)。

**有 OSIS MCP 的 `execute_python` 就用它跑**(工具名可能带宿主前缀,按后缀认):它用 OSIS 环境的 Python,自带 pyosis,并连到指定实例,自动模式读到的就是该实例的工程。终端里的 `python` 可能没装 pyosis,多实例时还可能连错实例。`execute_python` 不收命令行参数,用 `sys.argv` + `runpy` 传:

```python
import runpy, sys
script = r"<skill_dir>/scripts/test_conformance.py"
sys.argv = [script, "--bridge-type", "precast_small_box", "--is-continuous", "true"]
runpy.run_path(script, run_name="__main__")
```

总分 < 0.5 时脚本退出码 1,`execute_python` 会返回 `ok=false`(`SystemExit: 1`),报告仍在 stdout 里,照常读。没有 `execute_python` 时才用下面的终端写法。

**标准模式(显式传桥型,推荐)**:
```bash
python <skill_dir>/scripts/test_conformance.py \
    --candidate-dir <path> \
    --bridge-type cantilever_box \
    --is-continuous true
```

**自动模式(兜底:从 OSIS 当前项目读 py/,桥型从目录名猜;主跨从节点提取)**:
```bash
python <skill_dir>/scripts/test_conformance.py
```

**只指定候选目录**(桥型仍从目录名猜,目录名不含信息时回退 unknown,分数可能失真):
```bash
python <skill_dir>/scripts/test_conformance.py --candidate-dir <path>
```

**支持的可选参数**:
- `--is-prestressed BOOL` — 是否预应力
- `--concrete-ratio FLOAT` — 混凝土折算厚度 m³/m²
- `--beam-width FLOAT` — 桥宽 m
- `--output PATH` — 报告写到文件(默认 stdout)
- `--no-auto-detect` — 桥型识别不出时报错,不用 unknown 兜底
- `--list-bridge-types` — 列支持的桥型并退出

**退出码**:`0` = 总分 ≥ 0.5(可接受);`1` = 总分 < 0.5(不通过,便于脚本判断)。

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

## 桥型分支

所有桥型都出 D1–D5 五项,名称同报告标题,各项含义按桥型不同:

| 桥型 | 目录名兜底关键字 | D1 | D2 | D3 | D4 | D5 |
|---|---|---|---|---|---|---|
| cantilever_box | 悬浇/悬臂 | 支点梁高 | 跨中梁高 | 悬浇段梁高变化曲线 | 截面常规尺寸合理性判断 | 经济性与合理性 |
| rigid_frame | 刚构 | 支点梁高 | 跨中梁高 | 悬浇段梁高变化曲线 | 截面常规尺寸合理性判断 | 经济性与合理性(含边中跨比、墩高,无 D6) |
| t_girder | T 梁 / 矮 T 梁 | 跨径适配性 | 高跨比 | 截面常规尺寸 | 建设期经济性 | 标准化模板化指标 |
| precast_small_box | 小箱梁 | 跨径适配性 | 高跨比 | 截面常规尺寸 | 建设期经济性 | 标准化模板化指标 |
| cast_in_place_box | 现浇箱梁 | 跨径适配性 | 高跨比 | 截面常规尺寸 | 建设期经济性 | 结构完整性 |
| hollow_slab | 空心板 | 跨径适配性 | 高跨比 | 截面常规尺寸 | 截面经济性(空心率) | 建设期经济性 |
| unknown | 不匹配任一 | 同现浇箱梁(兜底,可能不准) | | | | |

T 梁按跨中马蹄自动分流:bh≤tw+2cm→矮T。

上表关键字**仅供兜底**:调用方没传 `--bridge-type` 时,CLI 才用 `detect_bridge_type(目录名)` 猜。大多数用户目录名不含桥型信息,猜不中会回退 `unknown`,分数失真——所以建模 AI 调用时务必显式传参。

## 注意事项

- **必须先建模**:`py/` 是空的话所有 D 项 = 0,总分 0,无意义
- **桥型由 AI 传入**:`bridge_type` / `is_continuous` 由调用方显式传入;目录名解析(`detect_bridge_type`)只是没传参时的兜底
- **主跨从节点提取**:不要用目录名或 `spans_from_name` 猜 L
- **不修改代码**:只读不写,出错(`fail`)只汇报,不自动改
