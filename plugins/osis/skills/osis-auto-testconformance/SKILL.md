---
name: osis-auto-testconformance
description: 桥梁构造建模正确性自动评测。在用户完成 `_1`..`_10` 模块建模(或模板套用)并写回 OSIS 后,**自动**调用 `model_conformance` 评分器按桥型规则评 OSIS 里的模型,生成总分 + D1~D5 分项报告 + 状态(ok/warn/fail)。用于完整建模(含模板复制/小修)完工后的自检;用户要求确认"这座桥构造是否合理"时也用这个。不要和 `osis-check`(荷载/规范验算)混用。
---

# osis-auto-testconformance

> 完整建模(含模板复制/小修)写回成功后,由总控自动跑一次,不需要用户开口;"越快越好"也不省略。局部修改、`osis-edit-hmid` 不跑,除非用户要求。
> 评测对象:**OSIS 里的模型,不是代码**。脚本把当前实例的模型导出为求解器命令流(`export_apdl`),用 pyosis 自带的 `transfer` 转回模板结构的 prep 代码(临时目录,不碰工程),再按桥型规则评分。代码怎么写(变量、循环、辅助函数、另一种 API)不影响得分。规则在本 skill 的 `scripts/model_conformance/`。

## 定位

| 干 | 不干 |
|---|---|
| 评 `model_conformance` 一个维度(构造合理性) | 验算荷载组合 / 规范 → `osis-check` |
| 出总分 + D1~D5 分项 + 状态 | 读求解结果(不需要求解) |
| 路由桥型 → 选对应规则 | 改任何代码或模型(只读不写) |

## 工作流

```
模型写回 OSIS(跑过 prep/main.py)
    │
    ▼
调用方(建模 AI)显式给出:bridge_type / is_continuous
    │  ※ 主跨 L 从节点/支座几何提取,不要从目录名猜
    ▼
execute_python 跑 test_conformance.py
    │  export_apdl → OSIS.out(临时目录)→ pyosis.transfer → prep 代码 → 按桥型规则评分
    ▼
展示给用户:总分 + 各 D 项 + 状态 + 原因 + 建议
```

### 调用方必传的参数

| 参数 | 含义 | 取值 |
|---|---|---|
| `bridge_type` | 桥型 | cantilever_box / rigid_frame / t_girder / precast_small_box / cast_in_place_box / hollow_slab |
| `is_continuous` | 是否连续梁 | true / false |

可选:`expected_L`(仅当节点提取不到主跨时兜底)、`is_prestressed`、`concrete_ratio`、`beam_width`——知道就传,不传规则按模型提取值兜底。

## 用法

`<skill_dir>` = 本 SKILL.md 所在目录。用 OSIS MCP 的 `execute_python` 跑(工具名可能带宿主前缀,按后缀认):它用 OSIS 环境的 Python,自带 pyosis,连到指定实例,读到的就是该实例的模型。`execute_python` 不收命令行参数,用 `sys.argv` + `runpy` 传:

```python
import runpy, sys
script = r"<skill_dir>/scripts/test_conformance.py"
sys.argv = [script, "--bridge-type", "precast_small_box", "--is-continuous", "true"]
runpy.run_path(script, run_name="__main__")
```

总分 < 0.5 时脚本退出码 1,`execute_python` 返回 `ok=false`(`SystemExit: 1`),报告仍在 stdout 里,照常读。导出失败(退出码 2)多半是模型还没写回 OSIS:先跑 `prep/main.py` 再评。

**读代码模式(只在没有 OSIS 时用)**:`--candidate-dir <工程的 py/ 目录>`(或模板目录,下面要有 `prep/`;给 `prep/` 本身会报错)。读的是代码,只有代码与模型一致时结果才可信:

```bash
python <skill_dir>/scripts/test_conformance.py --candidate-dir <py 目录> --bridge-type cantilever_box --is-continuous true
```

**可选参数**:
- `--expected-L FLOAT` — 节点提取不到主跨时的兜底
- `--is-prestressed BOOL` — 是否预应力
- `--concrete-ratio FLOAT` — 混凝土折算厚度 m³/m²
- `--beam-width FLOAT` — 桥宽 m
- `--output PATH` — 报告写到文件(默认 stdout)
- `--no-auto-detect` — 没传 `--bridge-type` 且目录名猜不出桥型时报错,不用 unknown 兜底
- `--list-bridge-types` — 列支持的桥型并退出

**退出码**:`0` = 总分 ≥ 0.5(可接受);`1` = 总分 < 0.5(不通过);`2` = 没评成(导出失败、目录不对)。

## 输出格式

markdown 报告大致形如(满分 1.0):

```
# <工程名> 构造建模正确性评定报告

## 项目概况
- 候选目录:<工程名>
- 桥型:cast_in_place_box
- 主跨 L:25.0 m
- 根部梁高 H_root:2.2 m
- 跨中梁高 H_mid:1.5 m
- 底板厚:T_root=0.22 m, T_mid=0.22 m
- 阶段数:4
- 总分:0.80 / 1.0
- 评级:良好 / Good

## 分项检查

### 2. D2 高跨比:0.00 / 1.0
- H/L:0.088
- 合理 H/L 区间:[0.0455, 0.0667]
- 状态:不符合
- 原因:H/L=0.0880 不在经验区间 [0.0455, 0.0667](H=2.2, L=25.0)
- 建议:建议调整梁高,使 H/L 落在合理区间

>>> model_conformance 总分: 0.8000  (满分 1.0)
```

每个 D 项都有 **状态**(符合要求 / 不符合等;对应 `ok` ≥ 0.9 / `warn` ≥ 0.5 / `fail` < 0.5),不符合时附 **原因** + **建议**。

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

上表关键字**仅供兜底**:没传 `--bridge-type` 时才用 `detect_bridge_type(工程名)` 猜。大多数工程名不含桥型信息,猜不中会回退 `unknown`,分数失真——所以必须显式传桥型。

## 注意事项

- **先写回再评**:评的是 OSIS 里的模型。改了代码没重跑 `prep/main.py`,评到的是旧模型;模型是空的则所有 D 项 = 0,无意义
- **不用求解**:只读模型的命令流,不需要、也不会触发求解
- **桥型由 AI 传入**:`bridge_type` / `is_continuous` 显式传;目录名解析只是兜底
- **主跨从节点提取**:不要用目录名或 `spans_from_name` 猜 L
- **只读不写**:出错(`fail`)只汇报,不自动改;导出写在临时目录,不动工程里的文件
