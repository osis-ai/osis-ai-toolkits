# 一次安全修复与回滚

## 进入修复

- 只接受 `visual_verdict = incorrect`。
- 要求只有一个待修问题，或多个问题最终收敛为同一个修改。
- 要求 `source_state_consistency = consistent`。
- 要求 `localization_status = exact`。
- 要求对象、字段和目标值全部唯一。
- 要求不存在未解决设计冲突。
- 任一条件不满足时设置 `repair_status = unsafe_to_apply`。

## 应用修改

- 在 `<run_dir>/rollback/` 备份每个待改源文件。
- 记录源文件、对象、字段、旧值、新值和修改理由。
- 将实际写入交接给 `osis-engine` 和对应 `osis-module-*`。
- 只修改当前项目 `py/prep/` 中已定位的字段。
- 保持 `repair_attempts <= 1`。
- 不得格式化无关代码，不得修改项目画像、模板、标准案例或其他 Skill。
- 不得尝试第二个目标值或第二个候选。

## 复核

- 重跑受影响模块和依赖闭包。
- 重新准备同一视图并截图。
- 复核修改区域、左右相邻对象和必要镜像区域。
- 同时检查目标值生效、原问题消失、边界连续、无新问题和白名单外状态未变。
- 复核结果为 `no_obvious_anomaly` 时设置 `repair_status = verified`。

## 回滚

- 复核仍为 `incorrect`、返回 `unjudgeable`、截图失败或结构后置条件失败时立即回滚。
- 从备份恢复全部已改文件。
- 重跑受影响模块并核对源文件恢复。
- 恢复完成时设置 `repair_status = rolled_back`。
- 恢复失败时设置 `repair_status = rollback_failed`。
- 二次截图失败时保留 `before_verdict = incorrect`，设置 `after_verdict = null`。
- 回滚后停止；不尝试第二个候选。
