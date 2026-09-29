# 常见工作流

## 0. 前置：确认 Broker 与实例

```text
list_instances()
```

- 返回 `[]` → 没有打开的 OSIS。告诉用户「当前没有运行中的 OSIS 实例」，不要猜端口。
- 返回 1 条 → 用它的 `instance_id`。
- 返回多条 → 按 `project` / `window_title` / `state` 判断；仍不确定就问用户。

操作前可再 `get_instance_info(instance_id)` 二次确认 `state` 是 `ready`（`busy` 表示正在算，等一下或问用户）。

## 1. 查询型

「查看我当前打开的 OSIS 模型有哪些」→ 只需 `list_instances`。

「这个模型有多少节点」：

```python
from pyosis import OSISEngine
engine = OSISEngine()
print(engine.model_summary())
```

只求解不改模型：

```python
engine.solve()
```

**不要**为了查询去跑 `main.py`（它会先 `clear()` 清空模型）。

## 2. 修改型（含写回 + 验证）

1. `get_api_help` 确认要用的 API。
2. 写最小脚本，`execute_python` 执行。
3. **写回**：若改的是 `py/prep/` 下的模板脚本，执行全量重建：

```python
import runpy
runpy.run_path(r"<project_dir>/py/prep/main.py", run_name="__main__")
```

4. **验证**：再执行一次查询脚本，确认改动生效。
5. 报告：改了什么、验证结果、做了哪些假设。

### 工程目录

从 `get_instance_info().project` 得到模型路径，工程的 `py/` 目录通常与模型同级或在其所在目录下。目录布局见 `osis-engine` 的 `references/template_layout.md`。

## 3. 完整建模

按 `osis-engine` 的编排走：任务分类 → 路由桥型 → 模板优先 → 模块 DAG → 生成 `py/prep/_1.._10.py` → 跑 `main.py` 写回 → 构造评测。

本 Skill 只补充执行方式：所有「跑脚本」都换成 `execute_python`。

## 4. API 未知时

```text
用户：给当前模型创建一个 XXX 类型单元
  ↓ 你不确定 API 名
get_api_help("创建 XXX 单元")
  ↓ 拿到签名与示例
execute_python(...)     ← 第一次可能报错
  ↓ 读 traceback
get_api_help(symbol="...")
  ↓ 修正
execute_python(...)     ← 成功
  ↓ 查询验证
报告
```

## 5. 多实例下改指定模型

「同时打开 bridge.osis 和 tower.osis，修改 bridge.osis 中的材料参数」：

1. `list_instances` → 用 `project` / `window_title` 含 `bridge` 的那个 `instance_id`。
2. 后续所有 `execute_python` 都带这个 ID。
3. **禁止**因为另一个实例是 `ready` 就改它。

## 6. 模糊多实例

「修改当前模型」且有两个以上实例、无法判断目标 → 问用户选哪个，不要默认挑第一个。

## 7. 异常恢复

`execute_python` 返回 `ok=false` 时：

1. 读 `exception.traceback`，定位是 API 名错、参数错还是逻辑错。
2. API 名/参数不确定 → `get_api_help`。
3. 改代码重试。**一次失败不代表 OSIS 不支持。**
4. 连续多次失败 → 把 traceback 关键部分给用户看，问是否换思路。

## 8. 实例闪退 / 重启

- 调用返回 `INSTANCE_OFFLINE` 或 `INSTANCE_NOT_FOUND` → 重新 `list_instances`。
- 若列表里出现新 ID（用户重启了 OSIS）→ 用新 ID，**不要**把旧 ID 映射过去。
- 向用户说明实例已重启、模型已重新加载。
