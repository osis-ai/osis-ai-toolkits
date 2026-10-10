---
name: osis-screenshot-check
description: 执行 OSIS 模型截图、当前项目画像对照、明显视觉异常定位、一次安全修复与复核。用户要求检查模型界面、判断建模代码造成的明显几何错误或自动修复视觉异常时使用。
---

# OSIS 模型视觉检查与自动修复

- 执行本技能期间不要再次加载 `osis-screenshot-check`(避免递归)。

## 接到任务后按顺序做

1. 取得当前 OSIS 项目目录，建立唯一 `run_dir`。
2. 冻结当前项目画像，准备指定视图。
3. 使用原生 UIA 定位画布，使用 WGC 截图。
4. 生成全梁图和左段、跨中段、右段三张放大图。
5. 直接对照当前项目画像判断明显视觉异常。
6. 判为 `incorrect` 后定位当前项目代码；必要时再检索一个标准案例。
7. 对唯一且安全的目标自动修复一次。
8. 重新准备视图、截图并复核；失败时立即回滚。

## 状态与边界

- 只处理 `OSISEngine().project.get_directory()` 返回的当前项目。
- 只在 `project_dir/runs/osis-screenshot-check/run_YYYYMMDD_HHMMSS/` 写入运行产物。
- 保持当前项目画像、桥型 Skill、标准案例、其他 Skill 和生产 `.out` 只读。
- 保持 `window_restore_attempts <= 1`、`capture_sets <= 2`、`repair_attempts <= 1`。
- 使用 `execution_status = completed | blocked` 记录流程状态。
- 使用 `screening_result = incorrect | no_obvious_anomaly | unjudgeable` 记录直接视觉结果。
- 仅在 `screening_result = incorrect` 时设置 `visual_verdict = incorrect`；其余设置 `visual_verdict = null`。
- 不得使用 PIL、NumPy 或阈值统计代替多模态视觉判断；程序只执行定位、截图、裁剪、路径与哈希校验。

## 1. 建立运行上下文

- 规范化 `project_dir`，创建并复用唯一 `run_dir`。
- 在任何视图或截图动作前执行：

  ```bash
  python -B "<skill_dir>/scripts/capture_canvas.py" freeze-profile \
    --project-dir "<project_dir>" --run-dir "<run_dir>" \
    --output "<run_dir>/project-profile-context.json"
  ```

- 首轮只对照冻结的当前项目画像。
- 首轮不得读取当前项目建模代码、实时模型摘要、桥型 Skill 或标准案例。
- 画像缺失、不可读、哈希变化或事实自相矛盾时设置 `screening_result = unjudgeable` 并停止。

## 2. 准备视图并截图

- 单独执行视图命令：

  ```bash
  python -B "<skill_dir>/scripts/view_control.py" prepare \
    --preset front --project-dir "<project_dir>" --run-dir "<run_dir>"
  ```

- 严格执行：

  ```python
  engine.run("plsm, 1")
  engine.run("/control,view,front")
  engine.replot()
  ```

- 任一步失败时设置 `execution_status = blocked` 并停止。
- 单独执行截图命令：

  ```bash
  python -B "<skill_dir>/scripts/capture_canvas.py" capture-auto \
    --project-dir "<project_dir>" --run-dir "<run_dir>" \
    --output "<run_dir>/before.png" --metadata "<run_dir>/before-capture.json" \
    --timeout 30
  ```

- 使用 Windows 原生 UI Automation 查找唯一 `Osis` 顶层窗口和唯一 `Name = 3D绘图`、`ControlType = Pane` 的画布。
- 使用 WGC 捕获窗口并按画布矩形裁剪。
- 仅在窗口最小化时恢复一次；不得聚焦、激活或置前窗口。
- 不得回退到全屏、GDI 或其他像素后端。
- 保持视图与截图命令独立；截图器不读取或校验 `view-command.json`。

## 3. 生成四张视觉输入

- 执行：

  ```bash
  python -B "<skill_dir>/scripts/capture_canvas.py" crop-views \
    --project-dir "<project_dir>" --run-dir "<run_dir>" \
    --source "<run_dir>/before.png" --prefix before
  ```

- 保留 `before-body.png`、`before-left.png`、`before-middle.png`、`before-right.png`。
- 使用一个 `before-visual-inputs.json` 记录四图路径、裁剪范围和 SHA-256。
- 排除工具栏、标签和大面积空白。
- 要求主体高度占比不低于 30%。
- 让左、中、右相邻分段保留少量重叠，避免异常落在裁剪边界。

## 4. 直接视觉判断

- 完整读取 `references/visual-rubric.md`。
- 将全梁图和左段、跨中段、右段四图作为图像加入当前对话并直接检查。
- 只把冻结的当前项目画像作为设计先验。
- 三段图只用于放大观察；不得要求逐点坐标、像素边缘锚定或穷举信号清单。
- 视觉有明显异常，或截图与当前项目画像明确不符时，直接设置 `visual_verdict = incorrect`。
- 为每个问题只记录 `issue_id`、`issue_type`、`region`、一句可见依据和可选粗略框。
- 无法直接查看图像内容、任一必要图像缺失、图像不足或画像含糊时设置 `screening_result = unjudgeable`、`visual_verdict = null`。
- 未发现明显异常时设置 `screening_result = no_obvious_anomaly`、`visual_verdict = null`。
- 输出“未发现明显视觉异常”；不得表述为“模型正确”。

## 5. 保存判断

- 按 `references/visual-rubric.md` 写入 `<run_dir>/visual-result.json`。
- 执行：

  ```bash
  python -B "<skill_dir>/scripts/capture_canvas.py" finalize-result \
    --project-dir "<project_dir>" --run-dir "<run_dir>" \
    --input "<run_dir>/visual-result.json" \
    --output "<run_dir>/run-manifest.json" \
    --profile-context "<run_dir>/project-profile-context.json" \
    --visual-inputs "<run_dir>/before-visual-inputs.json"
  ```

- 只校验字段、画像绑定、四图路径和哈希；不得用像素程序推翻视觉判断。
- 在无异常或无法判断分支把必要审计信息嵌入 `run-manifest.json` 后清理临时 JSON。
- 保存后重新读取 `run-manifest.json`，据此报告。

## 6. 定位并自动修复

- 仅在 `visual_verdict = incorrect` 时完整读取 `references/anomaly-rules.md`、`references/localization-schema.md` 和 `references/repair-policy.md`。
- 读取当前项目相关代码和当前 OSIS 只读摘要。
- 按“异常区域 → 相邻对象 → 源文件 → 对象/字段/目标值”定位。
- 不得把标准案例设为判错前置门禁。
- 仅在设计语义、目标值或对象映射仍不唯一时，按需检索一个最相关的桥型 Skill 或标准建模案例。
- 不得用近似案例提供修改数值。
- 要求项目状态一致，且对象、字段和目标值全部唯一。
- 不满足任一条件时设置 `repair_status = unsafe_to_apply` 并停止猜改。
- 先备份到 `<run_dir>/rollback/`，再冻结修改白名单。
- 将实际写入交接给 `osis-engine` 和对应 `osis-module-*`。
- 不得把建模 API 与桥型方案搬入本技能。
- 只修改当前项目中的唯一目标；不格式化无关代码，不修改模板或其他技能。

## 7. 二次复核与回滚

- 只重跑受影响模块和依赖闭包。
- 重新准备同一视图，生成 `after.png` 和必要的全梁、左、中、右或局部图。
- 对修改区域、相邻单元及必要镜像区域执行同一直接视觉判断。
- 原异常消失且无新异常时设置 `repair_status = verified`，保留 `before_verdict = incorrect` 和 `after_verdict = no_obvious_anomaly`。
- 仍为 `incorrect`、无法判断、截图失败或结构后置条件失败时立即回滚。
- 回滚成功时设置 `repair_status = rolled_back`；恢复失败时设置 `repair_status = rollback_failed`。
- 停止并且不尝试第二个候选。

## 参考

- 视觉输入与直接判断：`references/visual-rubric.md`
- 异常现象与常见代码原因：`references/anomaly-rules.md`
- 源文件定位与唯一性：`references/localization-schema.md`
- 备份、一次修复、复核与回滚：`references/repair-policy.md`
